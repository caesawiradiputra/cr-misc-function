# Fetch latest remote info
Write-Host "Fetching latest changes from origin..." -ForegroundColor Cyan
git fetch --all --prune

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to fetch from origin" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Fetch complete`n" -ForegroundColor Green

# Define protected branches
$protectedBranches = @("master", "dev", "sit")

# Verify all protected branches exist locally
Write-Host "Verifying protected branches exist..." -ForegroundColor Cyan
$localBranches = git branch --format="%(refname:short)" | ForEach-Object { $_.Trim() }

foreach ($branch in $protectedBranches) {
    if ($localBranches -notcontains $branch) {
        Write-Host "⚠️ Branch '$branch' does not exist locally" -ForegroundColor Yellow
    }
}

Write-Host ""

# Update master branch from origin
Write-Host "Updating master branch..." -ForegroundColor Cyan
git checkout master

if ($LASTEXITCODE -eq 0) {
    git reset --hard origin/master
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Master branch reset to origin/master" -ForegroundColor Green
        
        Write-Host "Pushing master to origin..." -ForegroundColor Yellow
        git push origin master --force
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Master branch pushed to origin`n" -ForegroundColor Green
        }
        else {
            Write-Host "❌ Failed to push master branch`n" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host "❌ Failed to reset master branch`n" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "❌ Failed to checkout master branch`n" -ForegroundColor Red
    exit 1
}

# Update dev branch from master
if ($localBranches -contains "dev") {
    Write-Host "Updating dev branch from master..." -ForegroundColor Cyan
    git checkout dev
    
    if ($LASTEXITCODE -eq 0) {
        git reset --hard origin/master
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Dev branch reset to origin/master" -ForegroundColor Green
            
            Write-Host "Pushing dev to origin..." -ForegroundColor Yellow
            git push origin dev --force
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Dev branch pushed to origin`n" -ForegroundColor Green
            }
            else {
                Write-Host "❌ Failed to push dev branch`n" -ForegroundColor Red
                exit 1
            }
        }
        else {
            Write-Host "❌ Failed to reset dev branch`n" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host "❌ Failed to checkout dev branch`n" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "⚠️ Dev branch does not exist, skipping...`n" -ForegroundColor Yellow
}

# Update sit branch from dev
if ($localBranches -contains "sit") {
    Write-Host "Updating sit branch from dev..." -ForegroundColor Cyan
    git checkout sit
    
    if ($LASTEXITCODE -eq 0) {
        git reset --hard origin/dev
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Sit branch reset to origin/dev" -ForegroundColor Green
            
            Write-Host "Pushing sit to origin..." -ForegroundColor Yellow
            git push origin sit --force
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Sit branch pushed to origin`n" -ForegroundColor Green
            }
            else {
                Write-Host "❌ Failed to push sit branch`n" -ForegroundColor Red
                exit 1
            }
        }
        else {
            Write-Host "❌ Failed to reset sit branch`n" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host "❌ Failed to checkout sit branch`n" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "⚠️ Sit branch does not exist, skipping...`n" -ForegroundColor Yellow
}

Write-Host "✅ All branches have been reset successfully!" -ForegroundColor Cyan
