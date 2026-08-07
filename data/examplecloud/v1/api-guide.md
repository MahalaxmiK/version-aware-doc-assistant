\# ExampleCloud API Guide



Product version: v1



\## Authentication



ExampleCloud API version 1 uses API keys. Clients must send the key in

the `X-API-Key` request header.



\## Request limits



Version 1 permits 100 API requests per minute for each account.



When the limit is exceeded, the API returns HTTP status code 429.



\## Data export



Version 1 supports CSV exports. JSON export is not available.

