"""
collector.py — File Collector dengan Kamus Default
"""
import os
from pathlib import Path
from typing import Iterable
from .ignore import IgnoreRules

# 1. DAFTAR EKSTENSI (Mencakup format ML, Cloud, KDL, dan varian Dotfiles)
CONFIG_EXTENSIONS = {
    # Format Standar & Data Serialization
    ".yaml", ".yml", ".json", ".json5", ".jsonc", ".toml", ".xml", ".ini", 
    ".cfg", ".conf", ".cnf", ".env", ".properties", ".prefs", ".plist",
    ".jsonnet", ".libsonnet", ".cue", ".dhall", ".hcl", ".bicep", ".nomad", ".hocon",
    
    # Format AI, Machine Learning, & Rust modern
    ".pbtxt", ".prototxt", ".kdl", ".ron", ".kcl", ".nickel",
    
    # Infrastructure, Cloud, & Container
    ".tf", ".tfvars", ".tfstate", ".tfstate.backup", ".sam", ".kubeconfig", 
    ".pipeline", ".workflow", ".ign", ".butane", ".bu", ".dockerfile",
    
    # Ekstensi Sistem & Git
    ".gitconfig", ".gitattributes",
    
    # Web, Proxy & SSL
    ".htaccess", ".htpasswd", ".pem", ".crt", ".cer", ".key", ".csr", ".ovpn",
    
    # Ekosistem Bahasa Pemrograman
    ".csproj", ".fsproj", ".vbproj", ".sln", ".props", ".targets", ".pom",
    ".gradle", ".cmake", ".make", ".mk", ".npmrc", ".yarnrc", ".pnpmfile", 
    ".pip", ".pypirc", ".coveragerc", ".gemrc", ".ruby-version", ".rbenv-version", 
    ".php_cs", ".php.ini", ".cargo", ".tool-versions", ".rspec", ".nvmrc",
    
    # Dependencies & Lockfiles
    ".lock", ".sum", ".mod", ".resolved",
    
    # Linter, Formatter & Rules
    ".eslintrc", ".prettierrc", ".stylelintrc", ".babelrc", ".browserslistrc", 
    ".yamllint", ".markdownlint", ".rego", ".prometheus", ".rules",
    
    # Ekstensi Ganda & Environment States
    ".local", ".dev", ".development", ".prod", ".production", ".test", 
    ".staging", ".qa", ".uat", ".default", ".example", ".sample", ".dist", 
    ".template", ".tmpl", ".tpl", ".j2", ".jinja", ".jinja2", ".override", 
    ".gotmpl", ".bak", ".backup", ".old", ".orig",
    
    # Tool-specific configs
    ".ansible", ".vault", ".sqlconf", ".policy", ".github", ".envrc", 
    ".mobileconfig", ".wxs", ".xcconfig", ".pbxproj", ".sfdx", ".reg", 
    ".sys", ".cfg.xml", ".settings", ".project", ".classpath", ".cproject", ".iml"
}

# 2. DAFTAR NAMA FILE PASTI (Mencakup file tanpa ekstensi dan config berbasis script)
CONFIG_EXACT_NAMES = {
    # Container, Orchestration & CI/CD
    "Dockerfile", "Containerfile", "docker-compose.yml", "docker-compose.yaml", 
    "compose.yml", "compose.yaml", "Vagrantfile", "Jenkinsfile", "Earthfile", 
    "Procfile", "Makefile", "kustomization.yaml", "Chart.yaml", "values.yaml", 
    "helmfile.yaml", "helmfile.yml", "skaffold.yaml", "skaffold.yml", 
    "serverless.yml", "buildspec.yml", "bitbucket-pipelines.yml", "appspec.yml",
    ".gitlab-ci.yml", ".travis.yml", ".codeclimate.yml", ".hound.yml",
    
    # JS/TS & Frontend Ecosystem 
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", 
    "npm-shrinkwrap.json", "lerna.json", "nx.json", "turbo.json", "tsconfig.json", 
    "jsconfig.json", "webpack.config.js", "vite.config.ts", "vite.config.js", 
    "rollup.config.js", "esbuild.js", "tailwind.config.js", "next.config.js", 
    "nuxt.config.js", "vue.config.js", "svelte.config.js", "jest.config.js", 
    "jest.config.ts", "babel.config.js", "babel.config.json", "postcss.config.js", 
    "playwright.config.ts", "cypress.config.js", "karma.conf.js", "protractor.conf.js", 
    "Gruntfile.js", "Gulpfile.js", "angular.json", "nest-cli.json", "nodemon.json", 
    "pm2.config.js", "ecosystem.config.js",
    
    # Python Ecosystem
    "pyproject.toml", "requirements.txt", "requirements.dev.txt", "Pipfile", 
    "Pipfile.lock", "poetry.lock", "setup.cfg", "setup.py", "tox.ini", "pylintrc", 
    ".pylintrc", "flake8", ".flake8", "pytest.ini", "mypy.ini", "black",
    
    # Go, Rust, Ruby, PHP, Java Ecosystem
    "go.mod", "go.sum", "Gopkg.toml", "Gopkg.lock", "golangci.yml", ".golangci.yml",
    "Cargo.toml", "Cargo.lock", "rust-toolchain", "rust-toolchain.toml",
    "Gemfile", "Gemfile.lock", "Rakefile", ".rubocop.yml", "Capfile", "Guardfile",
    "composer.json", "composer.lock", "phpunit.xml", "phpunit.xml.dist", "phpcs.xml", "phpstan.neon",
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", 
    "gradle.properties", "gradlew", "gradlew.bat", "mvnw", "mvnw.cmd", "checkstyle.xml",
    
    # Cloud & Hosting 
    "netlify.toml", "fly.toml", "wrangler.toml", "firebase.json", "database.rules.json", 
    "firestore.rules", "storage.rules", "app.yaml", "cron.yaml", "dispatch.yaml", 
    "index.yaml", "queue.yaml", "Pulumi.yaml", "Pulumi.dev.yaml", "terragrunt.hcl", "terraform.tfvars",
    
    # Mobile Apps
    "Podfile", "Podfile.lock", "Cartfile", "Cartfile.resolved", "Project.swift", 
    "Fastfile", "Appfile", "Matchfile", "Pluginfile",
    
    # Ignore Files & Git Configs
    ".gitignore", ".dockerignore", ".npmignore", ".helmignore", ".eslintignore", 
    ".prettierignore", ".terraformignore", ".csgignore", ".cfignore", ".slugignore", 
    ".ebignore", ".gitattributes", ".gitmodules", ".gitconfig",
    
    # System, Servers, & Generic Dotfiles
    ".env", ".env.local", ".env.development", ".env.test", ".env.production", 
    ".env.staging", ".env.example", ".env.sample", ".env.dist", ".env.template", 
    ".bashrc", ".zshrc", ".profile", ".editorconfig", "Caddyfile", "nginx.conf", 
    "httpd.conf", "supervisord.conf", "my.cnf", "postgresql.conf", "redis.conf", 
    "policy.yaml", "CODEOWNERS", "CNAME", "LICENSE", "application.properties", 
    "application.yml", "bootstrap.yml", "bootstrap.properties", "logback.xml", 
    "log4j2.xml", "server.xml", "context.xml", "web.xml", "MANIFEST.MF"
}

def collect_files(
    paths: list[str | Path], 
    extensions: list[str], 
    ignore: IgnoreRules
) -> Iterable[Path]:
    # Gunakan ekstensi dari config jika ada. Jika kosong, gunakan kamus default.
    if extensions:
        active_exts = {ext if ext.startswith('.') else f".{ext}" for ext in extensions}
    else:
        active_exts = CONFIG_EXTENSIONS

    # Pre-compute exact names (selalu diaktifkan!)
    exact_names_lower = {name.lower() for name in CONFIG_EXACT_NAMES}

    for base_path in paths:
        bp = Path(base_path)
        if not bp.exists():
            continue

        if bp.is_file():
            if not ignore.is_ignored(bp):
                yield bp
            continue

        for root, dirs, files in os.walk(bp):
            root_path = Path(root)

            dirs[:] = [d for d in dirs if not ignore.is_ignored(root_path / d)]

            for file in files:
                file_path = root_path / file
                
                if ignore.is_ignored(file_path):
                    continue

                # 1. Cek Exact Name (Case-Insensitive) - Sekarang SELALU JALAN
                if file_path.name.lower() in exact_names_lower:
                    yield file_path
                    continue

                # 2. Cek Ekstensi Konvensional
                suffix = file_path.suffix.lower()
                
                if not suffix and file_path.name.startswith('.'):
                    suffix = file_path.name.lower()

                if suffix in active_exts:
                    yield file_path