const REFRESH_INTERVAL = 5 * 1000

$(document).ready(function() {
	var walletsTable;
	
    walletsTable = $('#walletsTable').DataTable({
        ajax: {
            url: '/db/wallets',
            type: 'GET',
            dataSrc: ''
        },
        columns: [
            { data: 'name', type: 'string' },
            { data: 'date', defaultContent: "", type: 'string' },
            { data: 'time', defaultContent: "", type: 'string' },            
            { 
                data: 'address', 
                type: 'string',
                render: function (data, type, row) {
		            return '<a href="#" class="qr-link" data-wallet-name="' 
		                 + row.name 
		                 + '"><img class="qr-icon-small qr-icon" src="/images/poo_qr.png"></a>' 
		                 + '<button class="btn copyAddressBtn" data-clipboard-text="'
		                 + data
					     + '"><i class="fa fa-copy"></i></button>'
		                 + data;
                }
            },
            { data: 'lovelaces', type: 'string'}
        ],
        order: [[1, 'asc']], // order by second column (Name)
        initComplete: function(settings, json) {
            // Call the function to load lovelaces data
            loadAssetData();
                        
            // Start the timed function to refresh the data every 60 seconds
            setInterval(loadAssetData, REFRESH_INTERVAL);
        }
    });  

	$('#walletsTable').on('click', '.copyAddressBtn', function (event) {
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
			
	$('#walletsTable tbody').on('click', '.qr-link', function (event) {
		event.stopPropagation(); // Prevent event propagation to stop row expansion
		var tr = $(this).closest('tr');
		var rowData = walletsTable.row(tr).data();
		fetchQrCodeImage(rowData.name, rowData.address);
	});
	
    $('#walletsTable tbody').on('click', '.copyBtn', function(event) {
        event.stopPropagation(); // Prevent event propagation to stop row expansion
    });
    
	function fetchQrCodeImage(wallet_name, address) {
		$.ajax({
		    url: '/db/wallet/' + wallet_name + '/qr',
		    type: 'GET',
		    xhrFields: {
		        responseType: 'blob'
		    },
		    success: function (data) {
		        var blob = new Blob([data], { type: 'image/png' });
		        var qrCodeImageUrl = URL.createObjectURL(blob);

		        showQrModal(qrCodeImageUrl, wallet_name, address);
		    },
		    error: function () {
		        // Handle error if the QR code image cannot be fetched
		    }
		});
	}

	function showQrModal(qrCodeImageUrl, wallet_name, address) {
		var qrModal = $('#qrModal');
		var qrCodeImage = qrModal.find('#qrCodeImage');
		
		qrModal.find('#walletName').text(wallet_name);
		qrModal.find('#walletAddress').text(address);

		qrCodeImage.attr('src', qrCodeImageUrl);

		qrModal.modal('show');
	}

    function generateAssetsData(assets) {
        var assetsData = '<table cellpadding="5" cellspacing="0" border="0" style="padding-left:50px;">';
        if (assets && Object.keys(assets).length > 0) {
            $.each(assets, function(key, value) {
                assetsData += '<tr><td>' + key + ':</td><td>' + value + '</td></tr>';
            });
        } else {
            assetsData += '<tr><td>No assets</td></tr>';
        }
        
        assetsData += '</table>';
        return assetsData;
    }
        
	$('#walletsTable tbody').on('click', 'td', function () {
	    var tr = $(this).closest('tr');
	 var row = walletsTable.row(tr);

	    if (row.child.isShown()) {
	        // This row is already open - close it
	        row.child.hide();
	        tr.removeClass('shown');
	    } else {
	        var assets = row.data().assets; // get the assets from the row data
	        var assetsData = generateAssetsData(assets); // Generate the child row content
	        row.child(assetsData).show(); // Show the child row
	        tr.addClass('shown');
	    }
	});

	// Update function to load asset data
	function loadAssetData() {
		var rows = walletsTable.rows().nodes();
		rows.each(function(row, index) {
		    var rowData = walletsTable.row(row).data();
		    var walletName = rowData.name;

		    // Call the API to get the lovelaces data for the wallet
		    $.ajax({
		        url: '/db/wallet/' + walletName,
		        type: 'GET',
		        success: function(response) {
		            rowData.address = response.address;
		            rowData.date = response.date;
		            rowData.time = response.time;
		            rowData.lovelaces = response.lovelaces;
		            rowData.assets = response.assets; // add the assets to the row data
		            walletsTable.row(row).data(rowData).invalidate().draw(); // invalidate the data and draw the row

		            // If the row has a child and it's shown
		            if (walletsTable.row(row).child.isShown()) {
		                var tr = $(row);
		                var assetsData = generateAssetsData(response.assets); // Generate the child row content
  		                walletsTable.row(row).child(assetsData).show(); // Update the child row content and show it
 		                tr.addClass('shown');
		            }
   		        },
		        error: function() {
		            rowData.address = 'Error loading data';
		            walletsTable.row(row).data(rowData).invalidate();
		        }
		    });
		});
	}
});

