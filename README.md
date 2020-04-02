# AzureTokenExtractor
Extracts Azure authentication tokens from PowerShell process minidumps. More information on Azure authentication tokens and the process for using this tool, check out the corresponding blog post at https://www.lares.com/blog/hunting-azure-admins-for-vertical-escalation-part-2/.

## Usage
```
USAGE:
  python3 azure-token-extractory.py [OPTIONS]

OPTIONS:
  -d, --dump        Target minidump file
  -o, --outfile     File to save extracted Azure context
```
