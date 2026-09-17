# 403 Error Pattern — Dashboard "no permissions for [indices:data/read/search]"

## Error signature (dashboard logs)

```
[security_exception]: no permissions for [indices:data/read/search]
  and User [name=admin, backend_roles=[], requestedTenant=null]
GET /api/saved_objects/_find?type=index-pattern&fields=title&fields=fields&per_page=9999 403
```

The key detail: `backend_roles=[]` — the user "admin" authenticates with NO
backend_roles populated, even though the roles_mapping has backend_roles: ["admin"].
This means the mapping via backend_roles does NOT fire. The fix is to add "admin"
explicitly to the `users:` list in all_access.

## Same error in manager/filebeat logs

```
[security_exception]: no permissions for [cluster:monitor/main]
  and User [name=admin, backend_roles=[], requestedTenant=null]
Failed to connect to backoff(elasticsearch(https://wazuh.indexer:9200)): 403
```

Filebeat uses the same "admin" user and suffers from the same mapping gap.
After the fix, filebeat reconnects on its next retry (exponential backoff,
up to ~10 minutes).

## securityadmin.sh success output (expected)

```
Security Admin v7
Will connect to localhost:9200 ... done
Connected as "CN=admin,OU=Wazuh,O=Wazuh,L=California,C=US"
OpenSearch Version: 2.8.0
Contacting opensearch cluster 'opensearch' and wait for YELLOW clusterstate ...
Clustername: opensearch
Clusterstate: GREEN
Number of nodes: 1
Number of data nodes: 1
.opendistro_security index already exists, so we do not need to create one.
Populate config from /usr/share/wazuh-indexer
Force type: rolesmapping
Will update '/rolesmapping' with .../roles_mapping.yml
   SUCC: Configuration for 'rolesmapping' created or updated
SUCC: Expected 1 config types for node {"updated_config_types":["rolesmapping"],...} is 1 (["rolesmapping"]) due to: null
Done with success
```

## Dashboard recovery confirmation

After restart, logs should show all index-pattern requests as 200:
```
GET /api/saved_objects/_find?type=index-pattern... 200
GET /api/saved_objects/_find?fields=title&per_page=10000&type=index-pattern 200
GET /hosts/apis 200
GET /utils/configuration 200
POST /internal/search/opensearch 200
```
