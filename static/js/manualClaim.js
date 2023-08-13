$(function() {

	var claims_url

	$.ajax({
		type: 'GET',
		url: "claims_url",
		dataType: "json",
		timeout: 10000, // Set timeout to 10 seconds
		success: function(response) {
			claims_url = response.url;
		},
		error: function(xhr, status, error) {
			alert("Did not get back the claims_url which is odd!");
		}
	});

	$('#togglePassword').on('click', function() {
		var passwordInput = $('#password');
		var passwordType = passwordInput.attr('type');

		if (passwordType === 'password') {
			passwordInput.attr('type', 'text');
			$(this).text('Hide');
		} else {
			passwordInput.attr('type', 'password');
			$(this).text('Show');
		}
	});

	// Handle form submit event
	$('#fountainForm').on('submit', function(event) {
		event.preventDefault(); // Prevent default form submission behavior

		// Get form data
		const fountainName = $('#fountainName').val();
		const address = $('#address').val();
		const code = $('#code').val();
		const username = $('#username').val();
		const password = $('#password').val();

		// Construct request URL and data
		const url = `${claims_url}/${fountainName}`;
		const data = { address: address, claim_code: code };

		// Show sending status
		$('#statusPanel').removeClass('d-none');
		$('#statusSending').removeClass('d-none');
		$('#statusSuccess').addClass('d-none');
		$('#statusError').addClass('d-none');

		// Make POST request
		$.ajax({
			type: 'POST',
			url: url,
			data: JSON.stringify(data),
			contentType: 'application/json',
			timeout: 10000, // Set timeout to 10 seconds
			beforeSend: function(xhr) {
				// Set basic authentication header
				xhr.setRequestHeader('Authorization', 'Basic ' + btoa(username + ':' + password));
			},    
			success: function(response, textStatus, jqXHR) {
				// Show success status and response content
				$('#statusSending').addClass('d-none');
				$('#statusSuccess').removeClass('d-none');
				$('#statusCode').text(jqXHR.status);
				$('#responseBody').text(JSON.stringify(response, null, 2));
			},
			error: function(jqXHR, textStatus, errorThrown) {
				// Show error status and error message
				$('#statusSending').addClass('d-none');
				$('#statusError').removeClass('d-none');
				$('#errorCode').text(jqXHR.status);
				$('#errorMessage').text(jqXHR.responseText || errorThrown);
			}
		});
	});

	function getUrlParameter(name) {
		name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
		var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
		var results = regex.exec(location.search);
		return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
	}

	// Get Fountain Name and Code from URL parameters
	const fountainNameFromUrl = getUrlParameter('fountainName');
	const codeFromUrl = getUrlParameter('code');

	// Set Fountain Name and Code in the form fields
	$('#fountainName').val(fountainNameFromUrl);
	$('#code').val(codeFromUrl);
});
