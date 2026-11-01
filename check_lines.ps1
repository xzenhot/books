$lines = Get-Content 'd:\lab\github\books\.gitignore'
for ($i = 234; $i -le 239; $i++) {
    Write-Host ("Line {0}: [{1}] len={2}" -f $i, $lines[$i], $lines[$i].Length)
}