# ansible

Configura un PC con Pop!_OS 24.04 (o Ubuntu 24.04) recién formateado: paquetes, terminal, editor, git y Claude Code.
También se puede ejecutar en un PC que ya tiene cosas instaladas: los archivos que chocan con los dotfiles se mueven a `~/.dotfiles-backup/<fecha>` en vez de sobrescribirse.

## PC nuevo

```bash
sudo apt install -y ansible git
git clone https://github.com/JohnPosada/ansible.git ~/ansible
cd ~/ansible && ansible-playbook -K local.yml
```

La primera ejecución instala `gh` y se detiene, porque el repo `dotfiles` es privado. Inicia sesión y vuelve a ejecutarlo:

```bash
GH_BROWSER=true gh auth login --hostname github.com --git-protocol https --web   # cuenta JohnPosada
ansible-playbook -K local.yml
```

`GH_BROWSER=true` evita que abra un navegador; copia el código, presiona Enter y pégalo en https://github.com/login/device.

Ejecuta `ansible-playbook` en una terminal normal: no funciona desde el `!` de Claude Code.

## Cuentas de GitHub y firma de commits

Hay dos perfiles de git, definidos en `git_profiles` de `local.yml`:

| Perfil | Cuenta | Dónde se usa |
|---|---|---|
| personal | JohnPosada | por defecto |
| work | JohnPosada-arago | repos dentro de `~/arago/` y `~/CFdocgenerator/` |

- **Credenciales:** cada perfil pide a `gh` el token de su propia cuenta. No hay tokens en `~/.git-credentials`, que solo se usa para sitios que no son GitHub.
- **Firma:** cada PC genera una clave SSH de firma por perfil (`~/.ssh/id_ed25519_signing_<perfil>`) y la sube a GitHub, así los commits salen como *Verified*.

Para la cuenta de trabajo y la subida de claves, una vez por cuenta:

```bash
GH_BROWSER=true gh auth login --hostname github.com --git-protocol https --web   # cuenta JohnPosada-arago
gh auth switch -u JohnPosada       && GH_BROWSER=true gh auth refresh -h github.com -s admin:ssh_signing_key
gh auth switch -u JohnPosada-arago && GH_BROWSER=true gh auth refresh -h github.com -s admin:ssh_signing_key
ansible-playbook -K --tags git local.yml
```

Si falta algún permiso, el playbook lo indica al final con el comando a ejecutar.

## Sincronizar entre PCs

`dots sync` mantiene `~/dotfiles` igual en todos los PCs, incluida la configuración de Claude Code y las memorias de engram. Sube lo que cambió en este PC, trae lo del otro y aplica lo que llegó.

- Se ejecuta solo 5 minutos después de iniciar sesión y luego cada 24 horas (temporizador `dots-sync.timer`).
- `dots sync` lo ejecuta en el momento. Úsalo antes de cambiar de PC.
- `dots status` muestra la última sincronización, lo pendiente y la próxima ejecución automática.
- Si los dos PCs cambiaron la misma línea, se detiene sin tocar nada, avisa con una notificación y dice cómo resolverlo.
- Registro: `journalctl --user -u dots-sync`.

## Ejecutar solo una parte

```bash
ansible-playbook -K --tags <tag> local.yml
```

| Tag | Qué instala o configura |
|---|---|
| `install` | todo (igual que sin tags) |
| `apt` | paquetes del sistema (btop, ripgrep, fd, bat, ranger, tmux, copyq, flameshot, Java 17, Maven, pipx…) |
| `deb` | Google Chrome (repo apt) y Discord |
| `flatpak` | Slack, DBeaver, Edge, Spotify, OBS, Teams (cliente no oficial Teams for Linux), WhatsApp (ZapZap) |
| `docker` | Docker Engine y plugins, y añade tu usuario al grupo `docker` |
| `vscode` | VS Code (repo de Microsoft); se salta en WSL, donde `code` abre el de Windows |
| `intellij` | IntelliJ IDEA (edición unificada, básico gratis) en `~/.local/share/JetBrains/idea`, comando `idea`; se instala una vez y luego se actualiza desde el propio IDE; se salta en WSL |
| `cf` | Cloud Foundry CLI (`cf`); renueva su clave en cada ejecución porque Cloud Foundry la extiende cada año |
| `sapmachine` | SapMachine 17, el JDK de SAP (servidor local del SDK de Neo); queda como Java principal |
| `fonts` | fuentes de `fonts/` |
| `neovim` | bob y la última versión de Neovim, más lazygit |
| `lazygit` | solo lazygit |
| `node` | fnm y Node LTS |
| `npm` | paquetes npm globales (yarn) |
| `terminal` | kitty, zsh, oh-my-zsh, atuin y dotfiles |
| `kitty` | kitty como terminal predeterminada: Super+T en COSMIC, `mimeapps.list` y `x-terminal-emulator` |
| `cosmic` | atajos estilo GlazeWM: Alt y Super intercambiados, Alt+Space alterna con la ventana anterior del workspace (`wsfocus`, oculta la flotante que la tapa), Alt+Shift+Space flotante, Ctrl+Ñ abre CopyQ |
| `zsh`, `oh-my-zsh`, `atuin` | cada uno por separado |
| `dotfiles` | clona `dotfiles`, crea los enlaces con stow y activa `dots sync`; incluye `gh` y `git` |
| `git` | perfiles de git, claves de firma y `gh` |
| `gh` | solo GitHub CLI |
| `claude` | Claude Code, engram, graphify y la configuración guardada en `dotfiles/claude-code` |

Para saltarte algo: `--skip-tags flatpak`.

## Probar en Docker

```bash
./run.sh                                   # abre una shell en el contenedor
./run.sh --skip-tags flatpak               # ejecuta el playbook dentro
```

Flatpak no se puede probar en Docker (no hay D-Bus). Al probar con una sesión de `gh` real, añade `-e git_upload_signing_keys=false` para no subir a GitHub las claves del contenedor.
