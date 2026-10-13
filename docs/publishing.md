# Publishing SpecViz

SpecViz currently ships as a project-installed skill. The installer works with
Codex, Claude Code, and Antigravity; `tools/package.py` builds a standalone
skill ZIP. **Marketplace manifests, plugin bundles, and public listings have
not been added.** Use the [installation guide](installation.md) today.

The routes below were checked against official documentation on October 12,
2026. Publishing requirements can change.

## Keep one skill, package it for each host

Build each plugin from the same maintained `skills/specviz/` directory:

```text
skills/specviz/ - Shared instructions, helpers, and references
|
+-- Claude Code package   .claude-plugin/plugin.json
+-- Codex package         plugin.json with OpenAI listing metadata
+-- Antigravity package   plugin.json using Google's schema
```

Each bundle must carry the complete `skills/specviz/` directory and license.
Maintain small packaging definitions per host; generate the bundled copies.
Keep new framework readers independent of these distribution formats.

A marketplace catalog must resolve to published plugin files. An ignored
local `dist/` folder is not a usable GitHub source. Publish generated bundles
through a distribution branch or another source supported by the host, and
keep versions aligned with releases.

**The following commands describe the intended release setup. They are not
installation instructions for the current repository.**

## Claude Code

Create `.claude-plugin/plugin.json` in the plugin bundle. Add a
`.claude-plugin/marketplace.json` catalog to the GitHub distribution source,
with a marketplace name, owner, and an entry pointing to the plugin. Validate
the plugin and catalog with `claude plugin validate`. Once published, a
catalog named `specviz-marketplace` in this repository would allow:

```sh
claude plugin marketplace add bao96-bioinfo/SpecViz
claude plugin install specviz@specviz-marketplace
```

Plugin skills have a namespace: naming both the plugin and skill `specviz`
produces `/specviz:specviz overview`. Document this separately from the
standalone skill's `/specviz overview` command.
See [plugin structure](https://code.claude.com/docs/en/plugins) and
[marketplace setup](https://code.claude.com/docs/en/plugin-marketplaces).

For a public directory listing, submit the GitHub-hosted plugin through
[Anthropic's developer portal](https://claude.ai/directory/manage). A paid
Claude plan and the appropriate account role are required. Directory installs
can sync into Claude Code. The `claude-plugins-official` marketplace has a
separate partner route; submitting to the directory does not list a plugin
there. See [Anthropic's publishing guide](https://code.claude.com/docs/en/plugins/publish).

## Codex

Package the skill under `skills/specviz/` with a portable root `plugin.json`.
Put OpenAI-specific presentation metadata under `extensions.com.openai`;
`.codex-plugin/plugin.json` remains a supported compatibility format.

For repository distribution, add an `.agents/plugins/marketplace.json` catalog
that resolves to the published plugin. The current root `.agents/` ignore
rule would need a narrow exception for that catalog. Users would register it:

```sh
codex plugin marketplace add bao96-bioinfo/SpecViz
```

Catalog registration is a separate step from installing and enabling the
plugin. Follow the supported client's plugin interface and test the installed
copy. See [OpenAI's packaging and marketplace guide](https://developers.openai.com/plugins/build/plugins).

For the public directory shared by ChatGPT and Codex, upload the plugin ZIP in
the [OpenAI Plugins dashboard](https://platform.openai.com/plugins). Complete
publisher verification and listing metadata, resolve automated findings,
submit for review, and publish after approval. Skill updates require a new
ZIP. A skills-only package is supported; a hosted tool server is optional.
See [OpenAI's submission guide](https://developers.openai.com/plugins/deploy/submission).

## Antigravity (`agy`)

Build a plugin with a root `plugin.json` containing its name and description,
plus `skills/specviz/`. Use
[Antigravity's manifest schema](https://antigravity.google/docs/plugins);
do not assume its fields match OpenAI's portable manifest.

Once an Antigravity-compatible plugin is published at the repository root,
users can install it directly:

```sh
agy plugin install https://github.com/bao96-bioinfo/SpecViz
```

A generated local plugin can also be installed with
`agy plugin install /path/to/plugin`.

Official discovery currently uses `antigravity-plugins-official`. Google links
an [interest form](https://forms.gle/2EX5RFYPoJe1UgxR9) for getting a plugin
listed. Direct GitHub installation does not add a marketplace listing.
See [Antigravity's marketplace guide](https://antigravity.google/docs/marketplace?tab=cli).

## Suggested release order

1. Add host-specific packaging around the existing skill and generate bundles.
2. Validate manifests and test fresh plugin installs, commands, updates, and
   removal on each host. Existing standalone-skill acceptance does not cover
   marketplace installations.
3. Publish versioned distribution sources and release artifacts, with exact
   install commands in the README.
4. Submit the tested packages for directory review or marketplace consideration.

This keeps everyday development in one repository while giving each host the
package it expects. Marketplace approval remains a separate publishing step.


## Stable and beta release sources

`main` contains stable presentation. `beta` contains adaptive development and
retains the stable path for deferred hosts. Each source carries sealed channel,
version, and content identity metadata. The installer checks that metadata
before mutation; a branch name alone is not a release identity.

Prepare assets from their matching checkouts:

```sh
# Stable checkout
python3 tools/package.py --channel stable
# Beta checkout
python3 tools/package.py --channel beta
```

Each ZIP has a checksum receipt covering every packaged file and includes a
usable installer. Stable is `0.1.0`; adaptive is `0.2.0-beta.1`. Local `dist/` assets
are not public downloads. Before publishing, verify existing tags/releases and
choose a new version if the identifier is already used; never replace an asset
or tag. Publish beta as a prerelease and keep default installation on `main`.

Only after the beta branch has been published can readers fetch it with
`git clone --branch beta https://github.com/bao96-bioinfo/SpecViz.git SpecViz-beta`.
Until then, use the provided local beta checkout or extracted prerelease bundle.
Public release creation, marketplace publication, and promotion of adaptive
layout to stable are separate follow-up work.

The [prepared candidate record](release-candidates.json) records each local
archive's checksum and sealed skill identity. The accompanying `dist/*.json`
receipts cover every packaged file, including installer and setup guidance.
Both candidates were rebuilt byte-for-byte identically. Recheck these records
after any packaged-file edit; never reuse a published version for changed bytes.
