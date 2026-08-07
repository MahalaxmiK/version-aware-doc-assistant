\# ExampleCloud API Guide



Product version: v2



\## Authentication



ExampleCloud API version 2 uses OAuth 2.0 bearer tokens. Clients must

send the token in the `Authorization` request header.



\## Request limits



Version 2 permits 250 API requests per minute for each account.



When the limit is exceeded, the API returns HTTP status code 429.



\## Data export



Version 2 supports both CSV and JSON exports.

