# GitHub authentication for the laptop and Raspberry Pi

This guide configures GitHub access for this repository without putting
credentials in the checkout. Use a separate SSH key on each computer. The
laptop and a Pi can then fetch or push through Git over SSH without copying a
personal access token (PAT) between devices.

## Important: secure the existing PAT file

The old repository-root `git_token` file contained a PAT and had permissions
that allowed other local users to read it. Treat that token as exposed: revoke
it in GitHub under **Settings > Developer settings > Personal access tokens**,
then create a replacement only if you still need one. GitHub recommends
GitHub CLI or Git Credential Manager instead of manually creating a PAT for
command-line use. Treat every token like a password.

The file has been moved out of the repository to
`~/.config/fun-embed-sys/github_pat` with owner-only directory and file
permissions (`700` and `600`). This is a restricted-permission plaintext file,
not encrypted storage. Do not use it as a long-term credential store; revoke
the PAT and remove this file after the SSH setup below works. If a PAT must be
kept, use a password manager or OS credential vault rather than a text file.

The repository ignores `/git_token` as a safeguard. Never add a token, private
SSH key, credential cache, or `.env` file to Git, even in a private repository.

## Recommended setup: SSH keys

Create a separate key pair on the laptop and on each Pi that needs direct
GitHub access. Add only the `.pub` public key to GitHub; keep the private key
on the machine where it was generated. Never copy the laptop's private key or
PAT to a Pi. Use a passphrase when creating keys and load them through your
OS's SSH agent or keychain.

### Laptop

On the laptop, create a key if there is not already a suitable GitHub key:

```sh
ssh-keygen -t ed25519 -C "laptop-github"
```

Accept the default path or choose a clearly named key file. Enter a passphrase
when prompted. Add the public key to the SSH agent/keychain using your OS's
standard SSH-agent setup. Display the public key (safe to share with GitHub):

```sh
cat ~/.ssh/id_ed25519.pub
```

In GitHub, open **Settings > SSH and GPG keys > New SSH key**, paste the public
key, and save it. Test the connection:

```sh
ssh -T git@github.com
```

Change this repository's remote from HTTPS to SSH once the key works:

```sh
cd /path/to/fun-embed-sys
git remote set-url origin git@github.com:a143416/fun-embed-sys.git
git remote -v
```

The remote output should show the SSH URL for fetch and push.

### Raspberry Pi

SSH from the laptop to the Pi, then create a different key on the Pi:

```sh
ssh-keygen -t ed25519 -C "plex-pi-github"
cat ~/.ssh/id_ed25519.pub
```

Use a unique comment for each device, such as `salman-pi-github` or
`plex-pi-github`. Add this Pi's public key in GitHub under **Settings > SSH and
GPG keys > New SSH key** if the Pi needs the same account access as the laptop.
For a Pi that only needs to pull one repository, a repository **read-only
deploy key** is narrower: add its public key in the repository's **Settings >
Deploy keys**, leaving write access disabled. Do not share one private key
between the Pis.

On the Pi's checkout, use the SSH remote and test it:

```sh
cd /path/to/fun-embed-sys
git remote set-url origin git@github.com:a143416/fun-embed-sys.git
ssh -T git@github.com
git fetch origin
```

Use the Pi's own SSH-agent/keychain if the key has a passphrase. Once fetch
works, normal Git operations such as `git pull --ff-only` and `git push` use
the SSH key; they do not require a PAT file. A read-only deploy key supports
fetch/pull only.

## HTTPS alternative with GitHub CLI

If SSH is blocked by a firewall, install GitHub CLI (`gh`) from its official
installation instructions on that machine and sign in interactively:

```sh
gh auth login --hostname github.com --git-protocol https
gh auth setup-git
gh auth status
```

Choose the browser-based sign-in. GitHub CLI stores authentication in the OS
credential store when available; if it cannot find one, it may fall back to a
plaintext config file. Check the reported storage location and configure a
credential store before relying on HTTPS auth. Do not use `gh auth status
--show-token` or `gh auth token` in shared logs or terminal recordings because
they print credentials.

On a headless Pi, `gh auth login` can show a one-time browser/device flow.
Complete it on the laptop while the code is valid, and let `gh` store its
credential on the Pi. Never paste the PAT into the SSH command, a shell
command-line argument, this repository, or a chat.

## If a PAT is still required

Prefer a fine-grained PAT restricted to this repository, grant only the
permissions required (for Git operations, repository contents read/write as
needed), and set an expiration. Prefer GitHub CLI or Git Credential Manager
to store/use it. If a temporary file is unavoidable, keep it outside every
Git checkout, use owner-only permissions, and remove it after importing the
credential into a proper credential store. Never copy the laptop's PAT file to
a Pi; authenticate each device independently.

## References

- [GitHub: Managing personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [GitHub: Generate and add an SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
- [GitHub CLI: `gh auth login`](https://cli.github.com/manual/gh_auth_login)
- [GitHub: Cache credentials for Git](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git)
