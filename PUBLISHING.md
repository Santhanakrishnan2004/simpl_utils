# Packaging and publishing simplutils

How to turn this project into an installable package and, when you're ready, put it on PyPI
(or share it privately). **Nothing in this guide has been uploaded anywhere**; the package has only
been built and tested locally.

---

## 0. Pick how you want to share it

| Goal | Method | Needs an account? |
|---|---|---|
| Publish the source / install directly from GitHub | **GitHub** (section 1) | GitHub |
| Try it yourself / a few colleagues | **Share the wheel file** (section 5) | No |
| Your company / team only | **Private package feed** (section 9) | Your company's feed |
| Everyone: `pip install simplutils` | **PyPI** (sections 6-8) | Yes, free |

You can do them in that order. Starting with the wheel file costs nothing and commits you to nothing.

---

## 1. Publish the source to GitHub

1. Sign in to GitHub and create a **new public repository** named `simpl_utils`. Do not initialize it
   with a README, license, or `.gitignore`; those files already exist in this project.
2. Open PowerShell in this project folder (the folder containing `pyproject.toml`) and run:

   ```powershell
   git init
   git add .
   git commit -m "Initial release of simplutils"
   git branch -M main
   git remote add origin https://github.com/Santhanakrishnan2004/simpl_utils.git
   git push -u origin main
   ```

   If Git asks, configure your commit name and email with `git config --global user.name "Your Name"` and
   `git config --global user.email "you@example.com"`. GitHub will prompt you to authenticate when
   you push; do not put a password or access token in the remote URL. Use `main` exactly (not `mai`)
   as the branch name.
3. Check that the README and source files appear on the repository page. The GitHub project links
   are already configured in `pyproject.toml`. Anyone can install the current GitHub version with:

   ```powershell
   python -m pip install "git+https://github.com/Santhanakrishnan2004/simpl_utils.git"
   ```

   This installs from GitHub, not from PyPI. For the shorter, registry-based `pip install simplutils`
   command, continue with the PyPI release steps below.

---

## 2. Before the first release

1. **Name.** Check whether the `simplutils` distribution name is available immediately before
   releasing; names are only reserved when you upload:
   ```bash
   python -m pip index versions simplutils
   ```
   If a version is listed, the project name is already in use. If no matching distribution is found,
   still confirm the project name is available on PyPI before you build and upload.
2. **Licence.** `LICENSE` is MIT with the holder "simplutils contributors". Change the licence or the
   holder name if you want something else (for company work, check what your employer requires).
3. **Author and links** (optional but recommended). In `pyproject.toml`, add an `authors` entry.
   The `[project.urls]` links were configured in section 1. Use only details you're happy to make public.
   Anything in `pyproject.toml` and `README.md` becomes **public on PyPI** and cannot be edited
   for that version afterwards.
4. **Version.** It lives in one place: `__version__` in `src/simplutils/__init__.py`.

---

## 3. Set up a clean build environment

Use a virtual environment so the build tools don't disturb your other Python projects
(they can conflict with other installed packages).

```bash
# Windows PowerShell
python -m venv .venv-build
.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade build twine

# macOS / Linux / Git Bash
python -m venv .venv-build
source .venv-build/bin/activate        # Git Bash on Windows: source .venv-build/Scripts/activate
python -m pip install --upgrade build twine
```

---

## 4. Build

From the project folder (the one containing `pyproject.toml`):

```bash
python -m build
```

This creates two files in `dist/`:

| File | What it is |
|---|---|
| `simplutils-0.1.0-py3-none-any.whl` | The **wheel**: what `pip install` normally uses |
| `simplutils-0.1.0.tar.gz` | The **source archive** (sdist): for people who build from source |

Check them:

```bash
twine check dist/*          # both should say PASSED  (validates the README renders on PyPI)
```

Delete the `dist/` folder before every new build so old files aren't uploaded by accident.

---

## 5. Test the build in a clean environment (do this every time)

This proves the *built package* works, not just your source folder.

```bash
python -m venv .venv-test
.venv-test\Scripts\Activate.ps1                      # (bash: source .venv-test/bin/activate)

pip install dist/simplutils-0.1.0-py3-none-any.whl            # core only
simplutils --version
simplutils b64-encode "it works"

pip install "dist/simplutils-0.1.0-py3-none-any.whl[all]"     # with all extras
python examples/library_tour.py
python examples/cli_tour.py
```

**Sharing the wheel directly:** send `simplutils-0.1.0-py3-none-any.whl` to someone (email,
shared drive, chat). They run:

```bash
pip install simplutils-0.1.0-py3-none-any.whl            # add [all] before the closing quote for extras:
pip install "simplutils-0.1.0-py3-none-any.whl[all]"
```

The extras download their dependencies (Pillow, pypdf, ...) from PyPI automatically.

---

## 6. Create your PyPI accounts (one time)

1. Register at <https://pypi.org/account/register/> and **enable two-factor authentication** (required).
2. Register separately at <https://test.pypi.org/account/register/>. **TestPyPI** is a practice
   server: uploads there are throwaway and don't affect the real index.
3. Create an **API token** on each site (Account settings → API tokens).
   - For the first upload, use scope "Entire account" (the project doesn't exist yet).
   - After the first release, create a new token **scoped to the `simplutils` project only**, and delete the broad one.
4. **Treat tokens like passwords.** Never put them in the project folder, in git, or in a chat.
   A token starts with `pypi-`.

---

## 7. Upload to TestPyPI first (practice run)

```bash
twine upload --repository testpypi dist/*
```

When prompted: username `__token__`, password = your **TestPyPI** token.

Prefer not to type it? Set it for the current terminal only:

```powershell
# PowerShell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-xxxxxxxx"
```
```bash
# bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxx
```

Then install it from TestPyPI in a clean environment to see what a user would get:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ simplutils
simplutils --version
```

(`--extra-index-url` lets pip fetch the dependencies, which live on the real PyPI.)
Look at the project page that TestPyPI shows: the README, description and metadata are what
visitors will see.

---

## 8. Upload to the real PyPI

```bash
twine upload dist/*
```

Username `__token__`, password = your **PyPI** token. Then, in a clean environment, as any user would:

```bash
pip install simplutils
pip install "simplutils[all]"
simplutils --version
```

Your package page will be at `https://pypi.org/project/simplutils/`.

> **Uploads are permanent.** A version number can never be reused or replaced, even if you delete
> the release. If you find a mistake, fix it, bump the version, and upload again. Always do the
> TestPyPI practice run first.

### Releasing a new version later

1. Change `__version__` in `src/simplutils/__init__.py` (e.g. `0.1.0` → `0.1.1`).
   Use `MAJOR.MINOR.PATCH`: patch for fixes, minor for new tools, major for breaking changes.
2. Run the tests: `python -m pytest`.
3. Delete `dist/`, then `python -m build`, `twine check dist/*`.
4. Test in a clean environment (section 5), upload to TestPyPI (optional), then `twine upload dist/*`.

### Later: automatic publishing (recommended once it's in GitHub)

PyPI supports **Trusted Publishing**, which lets a GitHub Actions workflow upload releases without
any stored token. Set it up under your project's "Publishing" settings on PyPI, and use the
`pypa/gh-action-pypi-publish` action. It's safer than tokens, but needs a repository first.

---

## 9. Sharing inside a company (private)

If you don't want it public, there are good options:

- **Share the wheel** (section 5). Simplest.
- **A private package feed** (Azure Artifacts, JFrog Artifactory, Nexus, GitLab/GitHub package
  registry, or a self-hosted `devpi`). Your IT team will tell you which one exists. Upload with
  `twine upload --repository-url <feed-url> dist/*`, and install with
  `pip install --index-url <feed-url> simplutils`.
- **Install straight from a git repository:** `pip install "git+https://<your-git-host>/<repo>.git"`.
- **A standalone `.exe`** for people without Python is possible with tools like PyInstaller. That
  hasn't been set up or tested in this project.

If you publish internally, the PyPI name clash no longer matters, but keeping the `simplutils` name
means a later move to PyPI needs no code changes.

---

## 10. Pre-release checklist

- [ ] `python -m pytest` passes
- [ ] Version bumped in `src/simplutils/__init__.py`
- [ ] `README.md` reads well (it is the PyPI front page)
- [ ] No secrets, personal data or internal URLs in `pyproject.toml`, the README, or `examples/`
- [ ] Old `dist/` deleted, fresh `python -m build`, `twine check dist/*` passes
- [ ] Wheel tested in a **clean** environment (core and `[all]`)
- [ ] TestPyPI practice upload looked right
- [ ] Name still free (first release only)

## Troubleshooting

| Problem | Cause / fix |
|---|---|
| `403 Invalid or non-existent authentication` | Wrong token, or a TestPyPI token used on PyPI (they're separate). Username must be exactly `__token__` |
| `400 File already exists` | That version was already uploaded. Bump the version and rebuild |
| `403 ... isn't allowed to upload to project` | The name belongs to someone else, or your token is scoped to a different project |
| `twine check` fails on the README | Fix the Markdown, rebuild, re-check |
| Dependency conflicts when installing the build tools | Use a virtual environment (section 3). This project's build tools need a newer `packaging` than some other global packages allow |
