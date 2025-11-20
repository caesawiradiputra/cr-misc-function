# Fetch latest remote info (prune removes remote-tracking branches that no longer exist)
git fetch --all --prune

# Get list of all local branches
$localBranches = git branch --format="%(refname:short)" | ForEach-Object { $_.Trim() }

# Define branches to protect from deletion
$protectedBranches = @("main", "master", "dev", "sit")

# Update protected branches by switching and pulling from origin
Write-Host "Updating protected branches..." -ForegroundColor Cyan

$branchesToUpdate = @("master", "dev", "sit")

foreach ($branch in $branchesToUpdate) {
    if ($localBranches -contains $branch) {
        Write-Host "`nSwitching to '$branch'..." -ForegroundColor Yellow
        git checkout $branch
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Pulling latest changes from origin/$branch..." -ForegroundColor Yellow
            git pull origin $branch
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] Successfully updated '$branch'" -ForegroundColor Green
            }
            else {
                Write-Host "[WARN] Failed to pull '$branch'" -ForegroundColor Red
            }
        }
        else {
            Write-Host "[WARN] Failed to switch to '$branch'" -ForegroundColor Red
        }
    }
    else {
        Write-Host "Branch '$branch' does not exist locally, skipping..." -ForegroundColor Gray
    }
}

Write-Host "`n[OK] All protected branches updated!" -ForegroundColor Cyan

# Get list of all remote branches
$remoteBranches = git branch -r --format="%(refname:short)" | ForEach-Object {
    # Convert remote branch format like 'origin/feature/test' to 'feature/test'
    ($_ -replace "^origin/", "").Trim()
}

Write-Host "`nChecking local branches for cleanup..." -ForegroundColor Cyan

foreach ($branch in $localBranches) {
    if ($protectedBranches -contains $branch) {
        Write-Host "Skipping protected branch '$branch'" -ForegroundColor Blue
        continue
    }

    if ($remoteBranches -notcontains $branch) {
        Write-Host "Deleting local branch '$branch' (no longer exists on remote)" -ForegroundColor Yellow
        git branch -D $branch
    }
    else {
        Write-Host "Keeping '$branch'" -ForegroundColor Green
    }
}

Write-Host "`n[OK] Done! Local branches cleaned up." -ForegroundColor Cyan
