$(document).ready(function () {
	var showClaimedView = false;
	var selectedFountainId;
	var data_loaded

	var fountainTableConfiguration = $('#fountainTableConfiguration').DataTable({
    	ajax: {
			url: '/db/fountains',
			type: 'GET',
			dataSrc: ''
		},
		columnDefs: [
			{ targets: 2, className: 'dt-center' },
			{ targets: 3, className: 'dt-center' },
			{ targets: 5, className: 'dt-center' }
		],
		columns: [
			{ data: 'name', type: 'string' },
			{ data: 'status', type: 'string' },
			{ data: 'start_date', type: 'date' },
			{ data: 'end_date', type: 'date' },
			{ data: 'wallet', type: 'string' },
			{ data: 'max_address_claims', type: 'int' },
			{
				data: 'actions',
				type: 'html',
				render: function (data, type, row) {
					var actions = $('<div>');
					var dropdownBtn = $('<button>').text('Actions').addClass('btn btn-primary dropdown-toggle').attr('data-toggle', 'dropdown');
					var dropdownMenu = $('<div>').addClass('dropdown-menu');
					dropdownMenu.append($('<a>').text('Update').addClass('dropdown-item update-action').attr('data-id', row.id));
					dropdownMenu.append($('<a>').text('Delete').addClass('dropdown-item delete-action').attr('data-id', row.id).attr('data-name', row.name));
					
					if (row.total_claim_codes != '-') {
						dropdownMenu.append($('<a>').text('View Codes').addClass('dropdown-item view-codes-action').attr('data-id', row.id).attr('data-name', row.name));
						
						toggleTestModeButtonText = row.test_mode ? 'Disable Test Mode' : 'Enable Test Mode'
						
                        dropdownMenu.append($('<a>')
                        	.text(toggleTestModeButtonText)
                        	.addClass('dropdown-item toggle-test-mode-action')
                        	.attr('data-id', row.id)
                        	.attr('data-test-mode', row.test_mode ? 'on' : 'off')
                        );
					} else {
						dropdownMenu.append($('<a>').text('Upload Codes').addClass('dropdown-item upload-codes-action').attr('data-id', row.id));
					}
                    
					actions.append(dropdownBtn);
					actions.append(dropdownMenu);
					return actions.html();
				}
			}
		],
		rowId: 'id',
		drawCallback: function() {
			$('.dropdown-toggle').dropdown();
		},
	});

	var fountainTableClaimed = $('#fountainTableClaimed').DataTable({
    	ajax: {
			url: '/db/fountains',
			type: 'GET',
			dataSrc: ''
		},
		columns: [
			{ data: 'name', type: 'string' },
			{ data: 'total_claim_codes', type: 'num'},
			{ data: 'total_claimed', type: 'num'}
		],
		rowId: 'id',
		drawCallback: function() {
			$('.dropdown-toggle').dropdown();
		},
	});
	
	$('#toggleViewBtn').on('click', function () {
		showClaimedView = !showClaimedView;
		if (showClaimedView) {
			$('#fountainTableConfiguration_wrapper').hide();
			$('#fountainTableClaimed_wrapper').show();
			$('#toggleViewBtn').text('Table View Configuration');
		} else {
			$('#fountainTableConfiguration_wrapper').show();
			$('#fountainTableClaimed_wrapper').hide();
			$('#toggleViewBtn').text('Table View Claimed');
		}
	});	

	// Event listeners for update and delete actions
	$('#fountainTableConfiguration tbody').on('click', '.update-action', updateFountain);
	$('#fountainTableConfiguration tbody').on('click', '.delete-action', deleteFountain);
	
	$('#fountainTableConfiguration tbody').on('click', '.view-codes-action', function() {
		var fountainId = $(this).data('id');
		var fountainName = $(this).data('name');
		window.location.href = 'claimCodes.html?fountainId=' + fountainId + '&fountainName=' + fountainName;
	});

	$('#fountainTableConfiguration tbody').on('click', '.upload-codes-action', function() {
		selectedFountainId = $(this).data('id');
		$("#uploadDialog").modal("show")
	});
	
	// Date time pickers
	$('#startDateTime').datetimepicker({ format: 'YYYY-MM-DD HH:mm:ss' });
	$('#endDateTime').datetimepicker({ format: 'YYYY-MM-DD HH:mm:ss' });

	function selectUpdatedRow(fountainTable, tableName, selectedId) {
		fountainTable.ajax.reload(function () {
		    if (selectedId) {
		        var table = $(tableName).DataTable();
		        table.rows().every(function () {
		            var rowData = this.data();
		            if (rowData.id == selectedId) {
		                $(table.row(this.index()).node()).addClass('selected-row');
		            }
		        });
		    }
		}, false);
	}

	function loadFountains(selectedId) {
		selectUpdatedRow(fountainTableConfiguration, "#fountainTableConfiguration", selectedId);
		selectUpdatedRow(fountainTableClaimed, "#fountainTableClaimed", selectedId);
	}
	
	function loadWallets() {
		$.ajax({
			url: '/db/wallets',
			type: 'GET',
			success: function (wallets) {
			    var selectElement = $('#fountainWallet');

			    selectElement.empty(); // Clear existing options

		        var emptyOption = $('<option>').val('').text('Select Wallet');
		        selectElement.append(emptyOption);
            
			    // Add an option for each wallet
			    wallets.forEach(function (wallet) {
			        var option = $('<option>').val(wallet.name).text(wallet.name);
			        selectElement.append(option);
			    });
			}
		});
	}

	function createOrUpdateFountain(event) {
		event.preventDefault();
		var fountainId = $('#fountainId').val();
		var method = fountainId ? 'PUT' : 'POST';
		var url = '/db/fountain' + (fountainId ? '/' + fountainId : '');
		var data = {
			name: $('#fountainName').val(),
			start_date: $('#startDateTime').data('date'),
			end_date: $('#endDateTime').data('date'),
	        wallet: $('#fountainWallet').val(),
	        max_address_claims: parseInt($('#fountainMaxAddressClaims').val())
		};

		$.ajax({
			url: url,
			type: method,
			data: JSON.stringify(data),
			contentType: 'application/json',
			success: function (response) {
				$('#fountainModal').modal('hide');
				var id = fountainId || response.id;
				loadFountains(id);
			}
		});
	}

	function updateFountain() {
		var fountainId = $(this).data('id');

		$.ajax({
			url: '/db/fountain/' + fountainId,
			type: 'GET',
			success: function (fountain) {
				$('#fountainId').val(fountain.id);
				$('#fountainName').val(fountain.name);
				$('#startDateTime').datetimepicker('date', fountain.start_date);
				$('#endDateTime').datetimepicker('date', fountain.end_date);
				$('#fountainWallet').val(fountain.wallet);
				$('#fountainMaxAddressClaims').val(fountain.max_address_claims);
				$('#fountainModal').modal('show');
			}
		});
	}

	function deleteFountain() {
		var fountainId = $(this).data('id');
		var name = $(this).data('name');
		if (confirm('Are you sure you want to delete the "' + name + '" fountain?')) {
			$.ajax({
				url: '/db/fountain/' + fountainId,
				type: 'DELETE',
				success: function () {
					loadFountains();
				}
			});
		}
	}

	$('#createFountainBtn').on('click', function () {
		$('#fountainForm')[0].reset();
		$('#fountainId').val('');
		$('#fountainModal').modal('show');
	});

	$('#fountainForm').on('submit', createOrUpdateFountain);
	
	function updateSampleExpected() {
		var fileType = $("#fileType").val();
		var separator = $("#separator").val();
		var assetSeparator = $("#assetSeparator").val();
		var assetToValueSeparator = $("#assetToValueSeparator").val();

		// Update the sampleExpected field based on the file type
		if (fileType === "csv") {
			$("#csvSeparatorFields").show();
			$("#sampleExpected").removeClass("json-sample").addClass("csv-sample"); // Add class for CSV
			var sampleData = "code1" + separator + "lovelaces" + assetToValueSeparator + "1500000" + assetSeparator + "hosky" + assetToValueSeparator + "5000\n";
			sampleData += "code2" + separator + "lovelaces" + assetToValueSeparator + "2000000" + assetSeparator + "hosky" + assetToValueSeparator + "10";
		} else if (fileType === "json") {
			$("#csvSeparatorFields").hide();
			$("#sampleExpected").removeClass("csv-sample").addClass("json-sample"); // Add class for CSV
			var sampleData = {
				"code1": {
					"lovelaces": "1500000",
					"hosky": "5000"
				},
				"code2": {
					"lovelaces": "2000000",
					"hosky": "10"
				}
			};
			sampleData = JSON.stringify(sampleData, null, 2);
		}
		$("#sampleExpected").val(sampleData);
	}
	
	$("#fileType, #separator, #assetSeparator, #assetToValueSeparator").change(function() {
		updateSampleExpected();
	});	

	$("#uploadBtn").click(function() {
		var fileType = $("#fileType").val();
		var separator = $("#separator").val();
		var assetSeparator = $("#assetSeparator").val(); // Get the asset separator value
		var assetToValueSeparator = $("#assetToValueSeparator").val(); // Get the asset to value separator value
		var fileInput = document.createElement("input");
		fileInput.type = "file";
		if (fileType === "csv") {
			fileInput.accept = ".csv";
		} else if (fileType === "json") {
			fileInput.accept = ".json";
		}
		fileInput.onchange = function(event) {
			var file = event.target.files[0];
			var reader = new FileReader();
			reader.onload = function(e) {
				data_loaded = {}
				var contents = e.target.result;
				if (fileType === "csv") {
					result = parseCSV(contents, separator, assetSeparator, assetToValueSeparator);
				} else if (fileType === "json") {
					result = parseJSON(contents);
				}
				
				if (result.errors.length > 0) {
				    showValidationFailure(result.errors);
				} else {
				    showValidationSuccess(result.data, result.summary);
					data_loaded = result.data
				}						
			};
			reader.readAsText(file);
		};
		fileInput.click();
	});
	
	function isBigInt(str) {
		try {
			BigInt(str);
			return true; // String is a valid BigInt
		} catch (error) {
			return false; // String is not a valid BigInt
		}
	}

	function parseCSV(contents, separator, assetSeparator, assetToValueSeparator) {
		var lines = contents.split("\n");
		var data = [];
		var errors = [];
		var successCount = 0;
		var assetTotals = {};

		for (var i = 0; i < lines.length; i++) {
			var line = lines[i].trim();
			if (line === "") continue; // Skip empty lines
			var parts = line.split(separator);
			if (parts.length !== 2) {
				errors.push("Invalid line format at line " + (i + 1) + ", cound not find the separator "+separator);
				continue;
			}
			var code = parts[0].trim();
			var assets = parts[1].trim();
			// Validate code and assets
			if (code === "") {
				errors.push("Missing code at line " + (i + 1) + ", before the separator "+separator);
				continue;
			}
			if (assets === "") {
				errors.push("Missing assets at line " + (i + 1) + ", after the separator "+separator);
				continue;
			}
			// Parse assets
			var assetPairs = assets.split(assetSeparator);
			var assetData = {};
			var foundLovelaces = false
			for (var j = 0; j < assetPairs.length; j++) {
				var asset = assetPairs[j].trim()
				var assetPair = asset.split(assetToValueSeparator);
				if (assetPair.length !== 2) {
				    errors.push("Asset "+asset+" could not be split with " +assetToValueSeparator+" at line "+ (i + 1));
				    break;
				}
				var assetName = assetPair[0].trim();
				if (assetName.toLowerCase() === "lovelaces") {
					assetName = assetName.toLowerCase()
					foundLovelaces = true
				}
				var assetQuantity = assetPair[1];
				if (!isBigInt(assetQuantity)) {
				    errors.push("Invalid asset quantity "+assetQuantity+" for "+asset +" at line " + (i + 1));
				    break;
				}
				assetQuantity = parseInt(assetQuantity);
				assetData[assetName] = assetQuantity;

				// Calculate asset totals
				if (assetTotals.hasOwnProperty(assetName)) {
				    assetTotals[assetName] += assetQuantity;
				} else {
				    assetTotals[assetName] = assetQuantity;
				}
			}

			if (!foundLovelaces) {
			    errors.push("You must supply lovelaces on line " + (i + 1));
			    break;
			}

			// Add code and assets to data array
			data.push({
				code: code,
				assets: assetData
			});
			successCount++;
		}

		var summary = {
			codeCount: successCount,
			assetTotals: assetTotals
		};

		return {
			data: data,
			summary: summary,
			errors: errors
		};
	}     

	function parseJSON(contents) {
		var data = [];
		var errors = [];

		try {
			var jsonData = JSON.parse(contents);

			for (var code in jsonData) {
				var assets = jsonData[code];
				var assetData = {};
				var foundLovelaces = false

				for (var assetName in assets) {
					var assetQuantity = assets[assetName];

					if (!isBigInt(assetQuantity)) {
						errors.push("Invalid asset quantity for code: " + code + "." + assetName + " of " + assetQuantity);
						break;
					}

					if (assetName.toLowerCase() === "lovelaces") {
						assetName = assetName.toLowerCase()
						foundLovelaces = true
					}

					assetQuantity = parseInt(assetQuantity);
					assetData[assetName] = assetQuantity;
				}

				if (Object.keys(assetData).length === 0) {
					errors.push("No valid assets found for code: " + code);
				}

				if (!foundLovelaces) {
					errors.push("You must supply lovelaces for code: " + code);
				}

				data.push({
					code: code,
					assets: assetData
				});
			}

			// Calculate asset totals
			// var assetTotals = {}
			var assetTotals = { "lovelaces": 0, "assets": 0};
			data.forEach(function(entry) {
				for (var assetName in entry.assets) {
					/* Return to this. It produces a list of assets that cant be seen in panel! Need to change view of them
					if (assetTotals.hasOwnProperty(assetName)) {
						assetTotals[assetName] += entry.assets[assetName];
					} else {
						assetTotals[assetName] = entry.assets[assetName];
					}
					*/
					if (assetName == 'lovelaces') {
						assetTotals['lovelaces'] += entry.assets[assetName]
					} else {
						assetTotals['assets'] += entry.assets[assetName]
					}
				}
			});

			var summary = {
				codeCount: data.length,
				assetTotals: assetTotals
			};

			return {
				data: data,
				summary: summary,
				errors: errors
			};
		} catch (error) {
			errors.push("Error parsing JSON file: " + error.message);
			return {
				data: data,
				errors: errors
			};
		}
	}

	function showValidationFailure(errors) {
		var out = "<ul>";
		for (var i = 0; i < errors.length; i++) {
			out += "<li>" + errors[i] + "</li>";
		}
		out += "</ul>";
		$("#validationFailureMessage").html(out);
		$("#validationFailureDialog").modal("show");
	    $("#uploadDialog").addClass("modal-disabled"); // Add the "modal-disabled" class to disable the upload modal
	}

	function showValidationSuccess(data, summary) {
		var out = summary.codeCount + " Codes found<br><br>";
		out += "<u>Asset Totals</u><br><br>" 
		out += summary.assetTotals.lovelaces + " : Lovelaces<br>";
		
		// Iterate over each asset in the summary
		for (var assetName in summary.assetTotals) {
			if (assetName !== "lovelaces") {
				out += summary.assetTotals[assetName] + " : " + assetName + "<br>";
			}
		}
		
		$("#validationSummary").html(out);
		$("#validationSuccessDialog").modal("show");
	    $("#uploadDialog").addClass("modal-disabled"); // Add the "modal-disabled" class to disable the upload modal
	}

	$("#validationSuccessDialog").on("hidden.bs.modal", function() {
	    $("#uploadDialog").removeClass("modal-disabled"); // Remove the "modal-disabled" class to enable the upload modal
	});

	$("#validationFailureDialog").on("hidden.bs.modal", function() {
	    $("#uploadDialog").removeClass("modal-disabled"); // Remove the "modal-disabled" class to enable the upload modal
	});

	$("#saveBtn").on("click", function() {
		var url = '/db/fountain/' + selectedFountainId + "/upload_claim_codes";

		$.ajax({
			url: url,
			type: "POST",
			data: JSON.stringify(data_loaded),
			contentType: 'application/json',
			success: function(response) {
				$('#uploadDialog').modal('hide');
				$('#validationSuccessDialog').modal('hide');
				loadFountains(selectedFountainId);
			},
			error: function(xhr, status, error){
				alert("FAILED!");
			}
		});

	});


    $('#fountainTableConfiguration tbody').on('click', '.toggle-test-mode-action', function() {
        var fountainId = $(this).data('id');
        var testMode = $(this).data('test-mode') === 'on';

        // Send the request to toggle the test mode for the fountain
        $.ajax({
            url: '/db/fountain/' + fountainId + '/toggle-test-mode',
            type: 'POST',
            data: JSON.stringify({ test_mode: !testMode }),
            contentType: 'application/json',
            success: function (response) {
                // Handle the response if needed
                // For example, you can reload the table data to reflect the updated test_mode value.
                fountainTableConfiguration.ajax.reload();
            },
            error: function (xhr, status, error) {
                // Handle errors
                alert("Failed to toggle test mode.");
            }
        });
    });
    
	updateSampleExpected();
	loadWallets();
});

