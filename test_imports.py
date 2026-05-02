import sys
import traceback

tests = [
    "from shared import Colors",
    "from shared import GlowBackground, AnimatedHeader",
    "from shared import GlowButton, OutlineButton",
    "from shared import ModernInput, ModernTextBox",
    "from shared import ModernCard, ModernProgressBar",
    "from shared import create_separator, create_spacer",
    "from shared import derive_key_pbkdf2, encrypt_aes_gcm",
    "from shared import encrypt_file, decrypt_file",
    "from shared import WorkerThread, SimpleWorker",
    "from shared import parse_version, compare_versions",
    "from module_system import BaseModule, ModuleRegistry, ModuleWindow, get_global_registry",
    "from modules.qr_code import QrCodeModule",
    "from modules.encrypter import EncrypterModule",
    "from modules.password_manager import PasswordManagerModule",
    "from modules.media_hub import MediaHubModule",
    "from modules.ram_cleaner import RAMCleanerModule",
    "from modules.pdf_reader import PDFReaderModule",
    "from modules.file_splitter import FileSplitterModule",
    "from modules.program_manager import ProgramManagerModule",
    "from modules.pc_performance import PCPerformanceModule",
]

fails = 0
for stmt in tests:
    try:
        exec(stmt)
        print(f"OK  {stmt}")
    except Exception as e:
        print(f"FAIL {stmt}")
        traceback.print_exc()
        fails += 1

print(f"\nResult: {len(tests) - fails}/{len(tests)} passed, {fails} failed")
