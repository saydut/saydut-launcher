"""
Shared utilities and UI components for Saydut Launcher
"""
from .ui_components import (
    # Colors
    Colors,

    # Backgrounds & Effects
    GlowBackground,
    AnimatedHeader,

    # Pills & Badges
    StatPill,
    StatusPill,
    ShimmerBadge,

    # Buttons
    button_style,
    GlowButton,
    OutlineButton,

    # Inputs
    ModernInput,
    ModernTextBox,

    # Cards & Containers
    ModernCard,
    GlassPanel,

    # Progress
    ModernProgressBar,

    # Helpers
    create_separator,
    create_spacer,
)

from .crypto_utils import (
    # Constants
    PBKDF2_ITERATIONS,
    KEY_LENGTH,
    NONCE_LENGTH,
    SALT_LENGTH,

    # Key Derivation
    derive_key_pbkdf2,
    constant_time_compare,

    # AES-GCM
    encrypt_aes_gcm,
    decrypt_aes_gcm,

    # File Encryption
    encrypt_file,
    decrypt_file,
    encrypt_bytes,
    decrypt_bytes,

    # Folder Encryption
    encrypt_folder,
    decrypt_folder,
)

from .version_utils import (
    parse_version,
    compare_versions,
    is_newer,
    format_version,
    get_major_version,
    get_minor_version,
    get_patch_version,
)

from .threading_utils import (
    WorkerThread,
    SimpleWorker,
    run_in_thread,
)

__all__ = [
    # UI Components
    'Colors',
    'GlowBackground',
    'AnimatedHeader',
    'StatPill',
    'StatusPill',
    'ShimmerBadge',
    'button_style',
    'GlowButton',
    'OutlineButton',
    'ModernInput',
    'ModernTextBox',
    'ModernCard',
    'GlassPanel',
    'ModernProgressBar',
    'create_separator',
    'create_spacer',

    # Crypto
    'PBKDF2_ITERATIONS',
    'KEY_LENGTH',
    'NONCE_LENGTH',
    'SALT_LENGTH',
    'derive_key_pbkdf2',
    'constant_time_compare',
    'encrypt_aes_gcm',
    'decrypt_aes_gcm',
    'encrypt_file',
    'decrypt_file',
    'encrypt_bytes',
    'decrypt_bytes',
    'encrypt_folder',
    'decrypt_folder',

    # Version
    'parse_version',
    'compare_versions',
    'is_newer',
    'format_version',
    'get_major_version',
    'get_minor_version',
    'get_patch_version',

    # Threading
    'WorkerThread',
    'SimpleWorker',
    'run_in_thread',
]
