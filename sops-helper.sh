#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "bin" ]]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi
SOPS_CONFIG="$PROJECT_DIR/.sops.yaml"
ENV_FILE="$PROJECT_DIR/.env.local"
ENCRYPTED_FILE="$PROJECT_DIR/.env.sops"
AGE_KEY_DIR="${HOME}/.ssh/sops" #TODO: Change this to a more unique name if you want to manage multiple keys
AGE_KEY_FILE="${AGE_KEY_DIR}/soul" #TODO: Change this to a more unique name if you want to manage multiple keys
export SOPS_AGE_KEY_FILE="$AGE_KEY_FILE"

RED=$'\033[38;2;243;139;168m'
GREEN=$'\033[38;2;166;227;161m'
YELLOW=$'\033[38;2;249;226;175m'
CYAN=$'\033[38;2;203;166;247m'
BOLD=$'\033[1m'
NC=$'\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         󰌾  SOPS Secret Manager           ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

# ──────────────────────────────────────
# Commands
# ──────────────────────────────────────
cmd_encrypt() {
    print_banner

    if ! command -v sops &>/dev/null; then
        log_error "sops not found. Install: sudo pacman -S sops"
        return 1
    fi
    if [[ ! -f "$SOPS_CONFIG" ]]; then
        log_error ".sops.yaml not found. Run Keygen first"
        return 1
    fi
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "$ENV_FILE not found"
        return 1
    fi
    if grep -qF "age1..." "$SOPS_CONFIG" 2>/dev/null; then
        log_error ".sops.yaml has placeholder key. Run Keygen first"
        return 1
    fi

    if [[ -f "$ENCRYPTED_FILE" ]]; then
        log_warn "$ENCRYPTED_FILE already exists"
        read -p "Overwrite? (Y/n) " confirm
        if [[ "$confirm" =~ ^[Nn]$ ]]; then
            log_info "Cancelled"
            return 0
        fi
    fi

    if sops encrypt "$ENV_FILE" > "$ENCRYPTED_FILE"; then
        log_info "Encrypted: $ENV_FILE → $ENCRYPTED_FILE"
    else
        rm -f "$ENCRYPTED_FILE"
        log_error "Encryption failed"
        return 1
    fi
}

cmd_decrypt() {
    print_banner

    if ! command -v sops &>/dev/null; then
        log_error "sops not found. Install: sudo pacman -S sops"
        return 1
    fi
    if [[ ! -f "$ENCRYPTED_FILE" ]]; then
        log_error "$ENCRYPTED_FILE not found"
        return 1
    fi
    if grep -qF "age1..." "$SOPS_CONFIG" 2>/dev/null; then
        log_error ".sops.yaml has placeholder key. Run Keygen first"
        return 1
    fi

    if [[ -f "$ENV_FILE" ]]; then
        log_warn "$ENV_FILE already exists"
        read -p "Overwrite? (Y/n) " confirm
        if [[ "$confirm" =~ ^[Nn]$ ]]; then
            log_info "Cancelled"
            return 0
        fi
    fi

    if sops decrypt "$ENCRYPTED_FILE" > "$ENV_FILE"; then
        log_info "Decrypted: $ENCRYPTED_FILE → $ENV_FILE"
    else
        rm -f "$ENV_FILE"
        log_error "Decryption failed"
        return 1
    fi
}

cmd_keygen() {
    print_banner

    if ! command -v age-keygen &>/dev/null; then
        log_error "age-keygen not found. Install: sudo pacman -S age"
        return 1
    fi

    mkdir -p "$AGE_KEY_DIR"

    if [[ -f "$AGE_KEY_FILE" ]]; then
        log_warn "Key already exists at $AGE_KEY_FILE"
        read -p "Overwrite? (Y/n) " confirm
        if [[ "$confirm" =~ ^[Nn]$ ]]; then
            log_info "Keeping existing key"
        else
            rm -f "$AGE_KEY_FILE"
            age-keygen -o "$AGE_KEY_FILE" 2>/dev/null
            log_info "Key regenerated"
        fi
    else
        age-keygen -o "$AGE_KEY_FILE"
        log_info "Key generated"
    fi

    if [[ ! -f "$AGE_KEY_FILE" ]]; then
        log_error "Key file not found after generation"
        return 1
    fi

    local pubkey
    pubkey="$(grep -oP '# public key: \K.*' "$AGE_KEY_FILE" || true)"
    if [[ -z "$pubkey" ]]; then
        log_error "Could not extract public key"
        return 1
    fi

    if [[ ! -f "$SOPS_CONFIG" ]]; then
        cat > "$SOPS_CONFIG" <<SOPSYAML
creation_rules:
  - path_regex: \.env\.(local|sops)\$
    age: $pubkey
SOPSYAML
        log_info "Created $SOPS_CONFIG"
    else
        local existing_keys
        existing_keys="$(grep -oP '^\s+age:\s*\K.*' "$SOPS_CONFIG" || true)"
        existing_keys="$(echo "$existing_keys" | xargs)"

        if echo "$existing_keys" | tr ',' '\n' | xargs | grep -qF "$pubkey"; then
            log_info "Public key already in $SOPS_CONFIG"
        else
            if [[ -z "$existing_keys" || "$existing_keys" == "age1..." ]]; then
                local merged="$pubkey"
            else
                local merged="${existing_keys},${pubkey}"
            fi

            cat > "$SOPS_CONFIG" <<SOPSYAML
creation_rules:
  - path_regex: \.env\.(local|sops)\$
    age: $merged
SOPSYAML
            log_info "Added public key to $SOPS_CONFIG"
        fi
    fi

    echo ""
    echo -e "  ${BOLD}Public key:${NC} ${GREEN}$pubkey${NC}"
    echo ""
    echo "Share this key with your team so they can add it to .sops.yaml"
}

show_pubkey() {
    print_banner

    if [[ ! -f "$AGE_KEY_FILE" ]]; then
        log_error "No key found at $AGE_KEY_FILE"
        return 1
    fi

    local pubkey
    pubkey="$(grep -oP '# public key: \K.*' "$AGE_KEY_FILE" || true)"
    if [[ -z "$pubkey" ]]; then
        log_error "No public key found in $AGE_KEY_FILE"
        return 1
    fi

    echo -e "  ${BOLD}Public key:${NC}"
    echo ""
    echo -e "  ${GREEN}$pubkey${NC}"
    echo ""
    echo -e "  File: ${YELLOW}$AGE_KEY_FILE${NC}"
}

# ──────────────────────────────────────
# One-shot menu
# ──────────────────────────────────────
main() {
    if ! command -v fzf &>/dev/null; then
        log_error "fzf not found. Install: sudo pacman -S fzf"
        exit 1
    fi

    cd "$PROJECT_DIR"

    local choice
    choice=$(
        printf "%s\n" \
            "${GREEN}󰌾  Encrypt${NC}" \
            "${YELLOW}󰿆  Decrypt${NC}" \
            "${CYAN}!  Keygen${NC}" \
            "${CYAN}  Show Key${NC}" \
            "${RED}󰍃  Quit${NC}" \
            | fzf --ansi \
                --prompt="Select ❯ " \
                --reverse \
                --border \
                --info=inline \
                --header='╔══════════════════════════════════════════╗
║         󰌾  SOPS Secret Manager           ║
╚══════════════════════════════════════════╝'
    ) || true

    case "$choice" in
        *Encrypt*)  cmd_encrypt || true ;;
        *Decrypt*)  cmd_decrypt || true ;;
        *Keygen*)   cmd_keygen || true ;;
        *Show*Key*) show_pubkey || true ;;
    esac
}

main "$@"
