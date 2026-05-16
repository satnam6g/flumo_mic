# firewall_setup.ps1
# Adds or removes Windows Firewall rule for Wireless Mic UDP port 55555
# Usage:
#   Add rule:     powershell -ExecutionPolicy Bypass -File firewall_setup.ps1 -Action Add
#   Remove rule:  powershell -ExecutionPolicy Bypass -File firewall_setup.ps1 -Action Remove

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Add","Remove")]
    [string]$Action
)

$RuleName = "WirelessMicClient-UDP-55555"
$Port     = 55555
$Protocol = "UDP"

function Write-Status($msg) {
    Write-Host "[Firewall] $msg"
}

if ($Action -eq "Add") {
    # Remove existing rule first (idempotent)
    $existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Status "Rule already exists — updating."
        Remove-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
    }

    try {
        New-NetFirewallRule `
            -DisplayName  $RuleName `
            -Description  "Allow Wireless Mic Android app audio stream (UDP $Port)" `
            -Direction    Inbound `
            -Protocol     $Protocol `
            -LocalPort    $Port `
            -Action       Allow `
            -Profile      Any `
            -Enabled      True `
            -ErrorAction  Stop | Out-Null

        Write-Status "Firewall rule added: $RuleName (UDP $Port inbound)"
    }
    catch {
        Write-Status "ERROR: Could not add firewall rule: $_"
        # Fallback: legacy netsh command
        netsh advfirewall firewall add rule `
            name="$RuleName" `
            dir=in `
            action=allow `
            protocol=UDP `
            localport=$Port | Out-Null
        Write-Status "Fallback netsh rule applied."
    }
}
elseif ($Action -eq "Remove") {
    $existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
    if ($existing) {
        Remove-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
        Write-Status "Firewall rule removed: $RuleName"
    }
    else {
        # Also try legacy netsh removal
        netsh advfirewall firewall delete rule name="$RuleName" 2>$null
        Write-Status "Rule not found (already removed)."
    }
}
