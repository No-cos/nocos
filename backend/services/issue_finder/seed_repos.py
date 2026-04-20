# services/issue_finder/seed_repos.py
#
# Curated seed list of high-quality open source repositories that are
# guaranteed to have non-code contribution opportunities (documentation,
# design, translation, community, etc.).
#
# Why this exists:
#   The label-based GitHub Search discovery misses many well-known projects
#   that have active non-code work but don't use standard labels consistently.
#   Seeding the scraper with a hand-curated list ensures these projects are
#   always tracked without relying on label conventions.
#
# How it is used:
#   services/sync.py includes these repos in every discovery cycle so new
#   non-code issues from seed repos appear in the database promptly.
#
# Constraints:
#   - All standard filters still apply (age, closed, code-only, license).
#   - Repos with non-OSS licenses are silently skipped by build_project_data().
#   - Adding a repo here does not guarantee it appears on the platform — it
#     must have open non-code issues and pass the OPEN_SOURCE_LICENSES check.
#
# Format: list of (owner, repo) tuples.

SEED_REPOS: list[tuple[str, str]] = [

    # ── Documentation-heavy projects ─────────────────────────────────────────
    # These repos have large communities of writers, editors, and translators.
    ("freeCodeCamp", "freeCodeCamp"),           # Massive learning platform, constant doc/translation work
    ("EbookFoundation", "free-programming-books"),  # Community-curated book list (CC-BY-4.0)
    ("sindresorhus", "awesome"),                # Meta-list of awesome lists (CC0-1.0)
    ("public-apis", "public-apis"),             # Community-maintained API list (MIT)
    ("trimstray", "the-book-of-secret-knowledge"),  # Sysadmin knowledge base (MIT)
    ("tldr-pages", "tldr"),                     # Simplified man pages — translation-heavy (CC-BY-4.0)
    ("30-seconds", "30-seconds-of-code"),       # Code snippet docs — content contributions (CC-BY-4.0)
    ("jlevy", "the-art-of-command-line"),       # Translation-active command-line guide
    ("kamranahmedse", "developer-roadmap"),     # Community-maintained roadmap diagrams (CC-BY-SA-4.0)
    ("TheAlgorithms", "Python"),                # Algorithm docs and explanations (MIT)
    ("github", "docs"),                         # GitHub's own documentation (CC-BY-4.0)
    ("kubernetes", "website"),                  # k8s docs site — large translation effort (CC-BY-4.0)
    ("nodejs", "nodejs.org"),                   # Node.js official website and docs (MIT)
    ("rust-lang", "book"),                      # The Rust Programming Language book (MIT / Apache-2.0)
    ("mozilla", "mdn-content"),                 # MDN Web Docs — massive doc contribution community

    # ── Large foundations ─────────────────────────────────────────────────────
    # Well-resourced projects with established contributor programs.
    ("apache", "superset"),                     # Apache Superset BI tool (Apache-2.0)
    ("apache", "airflow"),                      # Apache Airflow — docs and community issues
    ("cncf", "landscape"),                      # CNCF landscape (Apache-2.0)
    ("django", "django"),                       # Django web framework (BSD-3-Clause)
    ("wordpress", "wordpress-develop"),         # WordPress core (GPL-2.0)
    ("grafana", "grafana"),                     # Grafana dashboards (AGPL-3.0)
    ("home-assistant", "core"),                 # Home Assistant (Apache-2.0)
    ("ansible", "ansible"),                     # Ansible automation (GPL-3.0)
    ("prometheus", "prometheus"),               # Prometheus monitoring (Apache-2.0)
    ("docker", "compose"),                      # Docker Compose (Apache-2.0)
    ("elastic", "elasticsearch"),               # Elasticsearch (Apache-2.0 on OSS branch)
    ("oppia", "oppia"),                         # Oppia interactive learning (Apache-2.0)
    ("mozilla", "gecko-dev"),                   # Firefox engine — large contributor base (MPL-2.0)

    # ── Design-friendly projects ──────────────────────────────────────────────
    # Projects that explicitly value UI/UX, accessibility, and visual design.
    ("tabler", "tabler"),                       # Open source admin dashboard (MIT)
    ("twbs", "bootstrap"),                      # Bootstrap CSS framework (MIT)
    ("ionic-team", "ionic-framework"),          # Ionic cross-platform UI (MIT)
    ("excalidraw", "excalidraw"),               # Collaborative whiteboard tool (MIT)
    ("ant-design", "ant-design"),               # Ant Design system (MIT)
    ("mui", "material-ui"),                     # Material UI component library (MIT)
    ("chakra-ui", "chakra-ui"),                 # Chakra UI (MIT)
    ("shadcn-ui", "ui"),                        # shadcn/ui component library (MIT)
    ("nickvdyck", "webbundlr"),                 # Web bundler — design contributions welcome
    ("tabler", "tabler-icons"),                 # Open source icon library (MIT)
    ("phosphor-icons", "phosphor-home"),        # Phosphor icon family (MIT)

    # ── Translation-active projects ───────────────────────────────────────────
    # Projects with active i18n/l10n communities or explicit translation pipelines.
    ("LibreTranslate", "LibreTranslate"),       # Open source machine translation (AGPL-3.0)
    ("nicehash", "NiceHashQuickMiner"),         # NiceHash miner — translation issues
    ("weblate", "weblate"),                     # Translation platform itself (GPL-3.0)
    ("element-plus", "element-plus"),           # Vue 3 component library — i18n active (MIT)
    ("vuetifyjs", "vuetify"),                   # Vuetify component library (MIT)
    ("frappe", "frappe"),                       # Low-code framework — active translation (MIT)
    ("omegat-org", "omegat"),                   # Open source CAT tool — translation (GPL-3.0)
    ("lingui", "js-lingui"),                    # i18n library — translation examples needed (MIT)

    # ── Community-driven projects ─────────────────────────────────────────────
    # Projects explicitly built around contributor community growth.
    ("firstcontributions", "first-contributions"),  # First-timer contribution guide (MIT)
    ("up-for-grabs", "up-for-grabs.net"),           # Up For Grabs project aggregator (MIT)
    ("EddieHubCommunity", "LinkFree"),              # Open source Linktree (MIT)
    ("codetriage", "codetriage"),                   # Issue triage community (MIT)
    ("open-sauced", "app"),                         # Open Sauced contributor analytics (Apache-2.0)
    ("storybookjs", "storybook"),                   # Storybook UI testing (MIT)
    ("prettier", "prettier"),                       # Code formatter (MIT)
    ("vercel", "next.js"),                          # Next.js framework (MIT)
    ("supabase", "supabase"),                       # Supabase BaaS (Apache-2.0)
    ("cal-com", "cal.com"),                         # Cal.com scheduling (AGPL-3.0)
    ("ghostery", "ghostery-extension"),             # Ghostery privacy extension (MPL-2.0)

    # ── Major OSS projects with non-code activity ─────────────────────────────
    # Large mainstream projects where non-code issues occasionally surface.
    ("microsoft", "vscode"),                    # VS Code editor (MIT)
    ("vuejs", "vue"),                           # Vue.js framework (MIT)
    ("angular", "angular"),                     # Angular framework (MIT)
    ("sveltejs", "svelte"),                     # Svelte framework (MIT)
    ("ohmyzsh", "ohmyzsh"),                     # Oh My Zsh shell config (MIT)
    ("neovim", "neovim"),                       # Neovim editor (Apache-2.0)
    ("PostHog", "posthog"),                     # PostHog product analytics (MIT)
    ("paperless-ngx", "paperless-ngx"),         # Document management (GPL-3.0)
    ("jellyfin", "jellyfin"),                   # Jellyfin media server (GPL-2.0)
    ("nocodb", "nocodb"),                       # NocoDB Airtable alternative (AGPL-3.0)
    ("directus", "directus"),                   # Directus headless CMS (GPL-3.0)
    ("outline", "outline"),                     # Outline team knowledge base (BSL — may be skipped)
    ("appsmith-org", "appsmith"),               # Appsmith low-code (Apache-2.0)
    ("getredash", "redash"),                    # Redash data visualisation (BSD-2-Clause)

]
