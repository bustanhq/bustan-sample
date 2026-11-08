# Cut a release

The project uses Semantic Versioning. A tag `vX.Y.Z` starts
`.github/workflows/release.yml`.

1. Select the next version from the changes under `[Unreleased]` in
   `CHANGELOG.md`: a breaking change increases the major version, a new
   feature the minor version, and a correction the patch version.

2. Set the version:

   ```bash
   uv version --bump minor
   ```

3. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`,
   and add a new empty `## [Unreleased]` above it.

4. Commit the two files:

   ```bash
   git commit -am "chore(release): cut X.Y.Z"
   ```

5. Make the tag, and push the commit and the tag:

   ```bash
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```

The workflow runs CI, makes sure that the tag is the version in
`pyproject.toml`, builds the distributions and the image, pushes the image to
`ghcr.io/<owner>/<repository>`, and publishes a GitHub release with the notes
of that version.

Never use a version two times. To correct a release, make a new patch
release.
