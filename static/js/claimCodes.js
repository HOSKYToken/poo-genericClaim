$(document).ready(function() {
	var fountainId = getUrlParameter('fountainId');
	var fountainName = getUrlParameter('fountainName');
	var claimCodesTable;
	var test_mode = false;
	var claims_url

	$.ajax({
		type: 'GET',
		url: "claims_url",
		dataType: "json",
		timeout: 10000, // Set timeout to 10 seconds
		success: function(response) {
			claims_url = response.url;
			populateDataTable();
		},
		error: function(xhr, status, error) {
			alert("Did not get back the claims_url which is odd!");
		}
	});

	function getUrlParameter(name) {
		name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
		var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
		var results = regex.exec(location.search);
		return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
	}

	function populateDataTable() {
		$.ajax({
			url: '/db/claimcodes/' + fountainId,
			type: 'GET',
			dataType: 'json',
			success: function (data) {
				test_mode = data.test_mode
				$('#pageHeading').text(test_mode ? 'Claim Codes (Test Mode)' : 'Claim Codes');

				claimCodesTable = $('#claimCodesTable').DataTable({
					data: data.claim_codes,
					columns: [
						{
							data: 'code',
							render: function (data, type, row) {
								var url = 'web+cardano://claim/v1?'
								    + 'faucet_url='
								    + claims_url.replace(':','%3A').replace('/','%2F')
								    + '%2F'
								    + fountainName
								    + '&code='
								    + data;
								    
								var url_data = new TextEncoder().encode(url)
								var url_hex = Array.prototype.map.call(url_data, function(byte) {
									return ('0' + byte.toString(16)).slice(-2);
								}).join('');

								return '<a href="#" class="qr-claim-link" data-claim-link="' 
								     +  url_hex
								     + '"><img class="qr-icon-small qr-icon" src="/images/poo_qr.png"></a>' 
								     + '<button class="btn copyCodeBtn" data-clipboard-text="' 
								     + data
								     + '"><i class="fa fa-copy"></i></button>'
								     + '<span>'
   								     + data
								     + '&nbsp;'
								     + '</span>';
							}
						},
						{ data: 'status', type: 'string' },
						{ data: 'lovelaces', type: 'num' },
				        {
				            data: null,
				            render: function (data, type, row) {
				                var actions = getActions(data);
				                if (actions.length > 0) {
				                	return '<div class="dropdown"><button class="btn btn-primary dropdown-toggle" data-toggle="dropdown">'
				                	     + 'Actions</button><div class="dropdown-menu">' + actions.join('') + '</div></div>';
				                } else {
				                	return "No Actions";
				                }
				            }
				        }
					],
					createdRow: function (row, data, index) {
						$(row).attr('data-id', data.id);					
						$(row).attr('data-assets', JSON.stringify(data.assets));
					}
				});

				claimCodesTable.on('click', 'tr', function (event) {
					var rowData = claimCodesTable.row(this).data();
					toggleRowDetails(this, rowData, claimCodesTable.row(this).index());
				});
				

				claimCodesTable.on('click', '.qr-claim-link', function(event) {
					event.preventDefault(); // Prevent default link behavior
					var claim_link = $(this).data('claim-link');
					var rowData = claimCodesTable.row($(this).closest('tr')).data();
					generateQrCodeImage(claim_link, 'Claim '+rowData.code);
					return false;
				});				
				
				claimCodesTable.on('click', '.qr-link', function (event) {
					event.stopPropagation(); // Prevent event propagation to stop row expansion
					var address = $(this).data('address');

					if (!address) {
						console.error("Address not found in the .qr-link data attribute.");
						return;
					}

					generateQrCodeImage(address);
				});

				$('#claimCodesTable').on('click', '.copyCodeBtn, .copyAddressBtn', function (event) {
					event.stopPropagation();

					var clipboardText = $(this).data('clipboard-text');
					var clipboard = new ClipboardJS(this, {
						text: function () {
						    return clipboardText;
						}
					});

					clipboard.on('success', function (e) {
						e.clearSelection();
						console.log('Copied to clipboard:', clipboardText);
					});

					clipboard.on('error', function (e) {
						console.error('Failed to copy to clipboard:', e);
					});

					// Trigger the copy action
					clipboard.onClick(event);
				});

			    updateClearAllTestClaimsButtonVisibility();				
			},
			error: function (xhr, status, error) {
				console.error('Error fetching data:', error);
			}
		});
	}
	
    function getActions(data) {
        var actions = [];
        
        if (test_mode && data.test_claim) {
            actions.push('<a class="dropdown-item" href="#" data-id="' + data.id + '" data-claim-id="' + data.claim_id + '">Clear Test</a>');
        }

        if (data.status === 'AVAILABLE') {
            actions.push('<a class="dropdown-item" href="#" data-id="' + data.id + '">Manually Test</a>');
        }

        return actions;
    }

    $('#claimCodesTable').on('click', '.dropdown-toggle', function(event) {
        event.stopPropagation();
        $(this).siblings('.dropdown-menu').toggleClass('show');
    });
    
       
    // Event listener for the actions dropdown items
    $('#claimCodesTable').on('click', '.dropdown-item', function (event) {
		var action = $(this).text();
		var code = $(this).closest('tr').find('td:first-child').text().trim();
		
        var claimId = $(this).data('claim-id');

        if (action === 'Clear Test') {
            // Send the request to clear the test claim
            $.ajax({
                url: '/db/fountain/' + fountainId + '/clear-test-claim/' + code,
                type: 'POST',
                success: function (claim_code) {
					var rowIndex = claimCodesTable.row('[data-id="' + claim_code.id + '"]').index();
					claimCodesTable.row(rowIndex).data(claim_code).invalidate();
					claimCodesTable.draw();                
                },
                error: function (xhr, status, error) {
                    // Handle errors
                    alert("Failed to clear test claim.");
                }
            });
        } else if (action === 'Manually Test') {
            var code = $(this).closest('tr').find('td:first-child').text().trim();
            var url = 'manualClaim.html?fountainName=' + encodeURIComponent(fountainName) + '&code=' + encodeURIComponent(code);
            window.open(url, '_blank');
        }

        $(this).parent().removeClass('show');
        
        return false;
    });    
    
	function generateQrCodeImage(content, hexType=null) {
		generate_url = '/db/qr/generate/' + content;		
		if (hexType) {
			generate_url += '/hex_encoded';
			content = hexType
		}
		
		$.ajax({
		    url: generate_url,
		    type: 'GET',
		    xhrFields: {
		        responseType: 'blob'
		    },
		    success: function (data) {
		        var blob = new Blob([data], { type: 'image/png' });
		        var qrCodeImageUrl = URL.createObjectURL(blob);
		        
		        showQrModal(qrCodeImageUrl, content);
		    },
		    error: function () {
		        // Handle error if the QR code image cannot be fetched
		    }
		});
	}

	function showQrModal(qrCodeImageUrl, address) {
		var qrModal = $('#qrModal');
		var qrCodeImage = qrModal.find('#qrCodeImage');
				
		qrModal.find('#walletAddress').text(address);

		qrCodeImage.attr('src', qrCodeImageUrl);

		qrModal.modal('show');
	}

	function toggleRowDetails(row, rowData, rowIndex) {
		var detailsRow = $(row).next('.row-details');
		var isRowExpanded = $(row).hasClass('row-details-open');

		// Check if the details section is already expanded
		if (isRowExpanded) {
		    $(row).removeClass('row-details-open');
		    detailsRow.remove();
		    return;
		}

		// Expand the details section
		$(row).addClass('row-details-open');

		// Build the HTML for the details section
		var assets = JSON.parse($(row).attr('data-assets'));

		var detailsRowHTML = '<tr class="row-details">';
		detailsRowHTML += '<td colspan="6">';

		if (rowData.claimed) {
		    detailsRowHTML += '<p>Claimed: ' + rowData.claimed + '</p>';
		    
		    detailsRowHTML += '<p>Address: '
							+ '<a href="#" class="qr-link" data-wallet-name="' 
							+ rowData.address 
							+ '"><img class="qr-icon-small qr-icon" src="/images/poo_qr.png"></a>' 
							+ '<button class="btn copyAddressBtn" data-clipboard-text="'
							+ rowData.address
							+ '"><i class="fa fa-copy"></i></button>'
							+ rowData.address
							+ '</p>';		    
		    
		    if (!rowData.test_claim) {
				cardanoScanLink = '<a href="https://cardanoscan.io/transaction/' + rowData.tx_hash + '"'
				                + ' target="_blank" rel="noopener noreferrer" class="cardano-scan-logo"></a>'
			    detailsRowHTML += '<p>Transaction Hash: ' + rowData.tx_hash + '&nbsp;' + cardanoScanLink + '</p>';
			}
		}

		if (assets && assets.length > 0) {
			detailsRowHTML += '<p>Assets:</p>';
			detailsRowHTML += '<ul>';
			assets.forEach(function (asset) {
				detailsRowHTML += '<li>' + asset.name + ': ' + asset.amount + '</li>';
			});
			detailsRowHTML += '</ul>';
		} else {
			detailsRowHTML += '<p>No assets</p>';
		}

		detailsRowHTML += '</td></tr>';

		detailsRow = $(detailsRowHTML);

	    var qrLink = detailsRow.find('.qr-link');
	    qrLink.data('address', rowData.address);

		// Insert the details section after the clicked row
		$(row).after(detailsRow);

		// Scroll to the expanded details section
		$('html, body').animate({
		    scrollTop: detailsRow.offset().top
		}, 500);
	}
			
    $('#exportCsvBtn').on('click', function() {
        exportTableToCSV();
    });

	function exportTableToCSV() {
		var tableData = claimCodesTable.rows({ search: 'applied', order: 'applied' }).data().toArray();

		// Prepare CSV header
		var csvContent = 'data:text/csv;charset=utf-8,';
		csvContent += 'Code,Status,Lovelaces,Address,Transaction Hash,Claimed\n';

		// Convert table data to CSV format
		tableData.forEach(function(row) {
		    var rowData = [
		        row.code,
		        row.status,
		        row.lovelaces,
		        row.address,
		        row.tx_hash,
		        row.claimed
		    ];
		    var rowCSV = rowData.map(function(value) {
		        return '"' + String(value).replace(/"/g, '""') + '"';
		    }).join(',');
		    csvContent += rowCSV + '\n';
		});

		// Create a temporary link element and trigger download
		var encodedUri = encodeURI(csvContent);
		var link = document.createElement('a');
		link.setAttribute('href', encodedUri);
		link.setAttribute('download', 'claim_codes.csv');
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
	}

    function hasTestClaims() {
        return claimCodesTable.rows().data().toArray().some(function(rowData) {
            return rowData.test_claim === true;
        });
    }

    // Update the visibility of the "CLEAR ALL TEST CLAIMS" button
    function updateClearAllTestClaimsButtonVisibility() {
        if (hasTestClaims()) {
            $('#clearAllTestClaimsBtn').show();
        } else {
            $('#clearAllTestClaimsBtn').hide();
        }
    }

	$('#clearAllTestClaimsBtn').on('click', function() {
		// Send the request to clear all test claims
		$.ajax({
		    url: '/db/fountain/' + fountainId + '/clear-all-test-claims',
		    type: 'POST',
		    success: function(resetClaimCodes) {
		        for (var i = 0; i < resetClaimCodes.length; i++) {
		            var resetClaimCode = resetClaimCodes[i];
		            var rowIndex = claimCodesTable.row('[data-id="' + resetClaimCode.id + '"]').index();
		            claimCodesTable.row(rowIndex).data(resetClaimCode).invalidate();
		        }
		        claimCodesTable.draw();

		        updateClearAllTestClaimsButtonVisibility();		    
		    },
		    error: function(xhr, status, error) {
		        // Handle errors
		        alert("Failed to clear all test claims.");
		    }
		});
	});
});

