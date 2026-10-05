# Git Workflow and CI/CD for Docker Image Deployment

## **Git Workflow for Python Application**

### **Branching Strategy**

* `master` → Production environment
* `dev` → Staging environment
* `sit` → SIT/UAT environment
* Feature and Fix branches follow naming conventions:

  * `fea/new-api-asset`
  * `fix/problem-module-not-found`

### **Workflow for New Features or Fixes**

1. Create a feature/fix branch from `sit`:

   ```sh
   git checkout -b fea/new-api-asset sit
   ```

2. Develop and commit changes locally.
3. Push changes to the feature/fix branch:

   ```sh
   git push origin fea/new-api-asset
   ```

4. Open a pull request (PR) to merge into `sit`.
5. Deploy `sit` branch to SIT/UAT for user testing.
6. If changes are approved, merge the feature/fix branch into `dev`.
7. Create a Docker image in `dev` using production environment variables.
8. If the image is validated, merge the feature/fix branch into `master`.
9. Delete feature/fix branches after merging.

### **Handling Fixes in SIT**

* If a fix is required during SIT testing, create a new fix branch from `sit`, make the changes, and follow the same workflow.
* If the fix is **specific to the SIT environment** (e.g., network config), commit directly to `sit` but document the change for future integration.

### **Rebasing and Merging**

* If `master` has updates, `dev` should be rebased or merged.
* If `dev` is updated, `sit` should also be rebased or merged.

## **Setting Up GitHub Actions for Docker Image Deployment**

### **Secrets Configuration in GitHub**

1. Go to your repository on GitHub.
2. Navigate to `Settings` → `Secrets and variables` → `Actions`.
3. Add the following secrets:

   * `ALIYUN_REGISTRY_USERNAME`: Your Alibaba Cloud container registry username.
   * `ALIYUN_REGISTRY_PASSWORD`: Your Alibaba Cloud container registry password.
   * `IMAGE_NAME`: The name of your Docker image repository.

### **GitHub Actions Workflow for Docker Image Build and Push**

Create a `.github/workflows/docker-image-ci.yml` file with the following content:

```yaml
name: Docker Image CI

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Docker Image Tag'
        required: true
        default: 'latest'

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    env:
      IMAGE_NAME: "ndf4w-1p4c-monitoring-airflow"  # Set your Docker image name here

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set IMAGE_TAG from input
      run: echo "IMAGE_TAG=${{ github.event.inputs.image_tag }}" >> $GITHUB_ENV

    - name: Log in to Alibaba Cloud Container Registry
      run: echo "${{ secrets.ALIYUN_REGISTRY_PASSWORD }}" | docker login --username=${{ secrets.ALIYUN_REGISTRY_USERNAME }} --password-stdin registry-intl.ap-southeast-5.aliyuncs.com

    - name: Build the Docker image
      run: |
        docker build -t registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }} .
        docker tag registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}

    - name: Push Docker Image to Alibaba Cloud
      run: |
        docker push registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}

```

### **Customizing the Workflow for Your Project**

* Change `registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/` to match your **Alibaba Cloud Container Registry namespace**.
* Update `secrets.IMAGE_NAME` with the actual **Docker image repository name**.
* Modify `default: 'latest'` in `image_tag` if you want a different default tag.

### **Running the Workflow Manually**

1. Go to the GitHub repository.
2. Navigate to `Actions`.
3. Select the `Docker Image CI` workflow.
4. Click `Run workflow`.
5. Enter a **Docker image tag** (e.g., `v1.2`) and start the workflow.

This ensures a structured and automated process for building and deploying Docker images to Alibaba Cloud. 🚀

---

## **Git Tag and Release Management**

### **Purpose of Git Tags**

Git tags are used to mark **immutable release points** in the repository. A tag always points to a specific commit and never moves. Tags are primarily used for:

* Production release identification
* Versioning (code, Docker images, packages)
* CI/CD triggers
* Rollback and audit purposes

---

### **Tag Creation Rules**

* Tags are created **only on the `master` branch**
* `master` must always come from a PR or merge from `dev`
* Never create tags on `dev`, `sit`, or feature branches

This ensures every tag represents a **production-ready state**.

---

### **Tag Naming Convention**

The repository follows **semantic versioning**:

```text
vMAJOR.MINOR.PATCH
```

Examples:

```text
v1.0.0
v1.1.0
v1.1.1
```

---

### **When to Create a Tag**

Tags are created **after a successful production promotion**:

1. Feature/Fix branch tested in `sit`
2. Feature/Fix branch merged into `dev`
3. Final package or Docker image validated in `dev`
4. `dev` merged into `master`
5. **Create and push a tag on `master`**

---

### **How to Create and Push a Tag**

```sh
git checkout master
git pull origin master

git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
```

Tags must never be force-updated or deleted once released.

---

### **GitHub Releases**

GitHub Releases are used as a **human-readable layer** on top of Git tags.

Best practices:

* Every production tag should have a corresponding GitHub Release
* Release notes should include:

  * Jira / ticket IDs
  * Summary of changes
  * Links to release artifacts (DDL, templates)
  * Docker image or package version

Example release note content:

```md
## Version v1.2.0

### Changes
- DA-1421: Add realtime exposure index
- DA-1470: Improve obligor rule evaluation

### Artifacts
- Docker image: da-af-rules-engine:v1.2.0
- Release scripts: /release/2024-11-18_DA-1421

### Deployment
- Deployed to production on 2024-11-19
```

---

### **CI/CD Integration with Tags (Optional)**

Tags can be used to trigger CI/CD pipelines to build production artifacts:

```yaml
on:
  push:
    tags:
      - 'v*'
```

Benefits:

* Docker image tags always match Git tags
* Guaranteed consistency between code and artifacts
* Simplified rollback using previous tags

---

### **Release and Tag Maintenance Rules**

* Feature and fix branches are deleted after merge
* Tags are permanent and must not be rewritten
* If a production issue occurs, create a new patch tag (e.g. `v1.2.1`)
* Never reuse or move existing tags
