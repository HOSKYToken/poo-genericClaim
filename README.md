## Proof of Onboarding (P.o.O) - Generic Claims

Welcome to the P.o.O generic claims tool. This has been developed by the HOSKY team (VEGAS Pool for blame), so don't expect much!

The tool has been written as a Python script that starts two WSGI compliant servers:

* Admin - see src/routes/admin.py
* Claims - see src/routes/claims.py

As the tool starts up, an Admin page shall be presented for you to configure P.o.O claim fountains. This Admin console should NEVER be exposed to the internet.

In fact this tool is a Beta proof of concept, i.e. it's NOT PRODUCTION ready by any stretch of the imagine.

What is it then? It's a template for teams to implement the P.o.O. specification found here [CIP-99](https://github.com/cardano-foundation/CIPs/pull/546)

The second server route is claims and it does exactly what is written on the tin. This is the code that processes the requests that are forwarded by the participating QR Scanning wallet (we've worked closely with the [VESPR wallet team](https://twitter.com/vesprwallet)).

This SHOULD be exposed to the internet and you should make sure you lock the server carefully with the port you configured exposed. All traffic is expected to be TCP over HTTPS.

As the process starts up, it will create a local sqlite3 database for you with the database schema found in the /src/database directory and the access via Database Access Objects (src/daos).

The Admin server utilises the content found in static for it's pages. These pages consist of HTML and Javascript and are desperate for a makeover by any GUI expert/team that wish to get involved. We could have embedded the pages into python, but these provide examples of how connectivity to the Claims and Admin routes work! The javascript has not been optimised nor tidied (be warned)!

Everything operates with a Cardano CLI. I.E. the process expects you to configure the path to one and it utilises this to:

* Create wallets (via a separate script)
* Obtain UTXO balance in the wallet
* Construct and send the airdrop assets 
* Monitor UTXOs to be sent in an airdrop

Clearly, this could all be written in other technology! Hence, this is simply a beta tool to prove things work.

To start the tool, you will need to install the requisite packages, for which there's an install_venv_and_libs script in scripts. The tool requires Python 3.10 and it makes sense to run this in a virtual environment. There is no promise that all packages are configured in that script. Please raise tickets if you notice any missing.

The tool is invoked by the poo.sh file found in Scripts. It is configured to expect to find a settings file in a folder of the same name (not in this repository due to sensitive information unique to each installation). Please replace:

* <YOUR_PATH> - in each location
* root_path - can be set and <root_path> in the rest of the settings is auto replaced for convenience when executing

The configuration allows for you to configure the path to the SSL keys required to enable the tool to operate over HTTPS. A script for creating a self-sign certificate has been provided as an example.

In the samples folder, there's also an example of a data.json file for uploading via the Admin page. It has a CSV and JSON upload option, although the CSV is far more complex than it needs to be, therefore I recommend people use the JSON. You simply provide a list of keys (in the example are uuids) and then a list of policy.name assets with amounts. The name may be in hex or ascii, the upload determines the types. I will also provide some generation scripts in the future as examples.

I will provide more details when I get time (heading to Denver soon), thus this is the first publication to make this available.

Good luck in using this! Kind regards

Vegas