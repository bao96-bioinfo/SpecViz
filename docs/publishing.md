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


## Stable release source

`main` is the maintained stable source. Adaptive beta is retired and new beta
install/package/release requests are rejected. A legacy beta ownership manifest
is still accepted for migration and removal; it is not a distributable source.

```sh
python3 tools/package.py --channel stable
```

Each ZIP includes the complete skill and installer, and has a checksum receipt
covering every packaged file. The current candidate is `0.1.1`; local `dist/`
assets are not public downloads. Before publishing, recheck existing tags and
releases and never replace an existing identifier with different bytes.
The [active candidate record](release-candidates.json) identifies the maintained
stable candidate. Earlier candidate identities remain in historical acceptance.
Marketplace packaging and publication remain separate follow-up work.
