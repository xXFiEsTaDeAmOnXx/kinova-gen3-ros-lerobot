import logging
import os
import select
import termios
import threading
import tty
from queue import Queue
from typing import Any

from lerobot.teleoperators.keyboard import KeyboardTeleop
from lerobot.utils.errors import DeviceNotConnectedError

from .config_keyboard_joint import KeyboardJointTeleopConfig

logger = logging.getLogger(__name__)

# Key layout:
#   Joint 1: Q(-) / A(+)    Joint 5: T(-) / G(+)
#   Joint 2: W(-) / S(+)    Joint 6: Y(-) / H(+)
#   Joint 3: E(-) / D(+)    Joint 7: U(-) / J(+)  (Gen3)
#   Joint 4: R(-) / F(+)    Gripper: O(close) / L(open)
#   Quit: Ctrl+C

KEY_MAPPINGS = {
    "q": (0, -1), "a": (0, +1),
    "w": (1, -1), "s": (1, +1),
    "e": (2, -1), "d": (2, +1),
    "r": (3, -1), "f": (3, +1),
    "t": (4, -1), "g": (4, +1),
    "y": (5, -1), "h": (5, +1),
    "u": (6, -1), "j": (6, +1),
}
GRIPPER_KEYS = {"o": -1, "l": +1}


def _open_tty():
    """Open /dev/tty directly — works even when stdin is a pipe/heredoc."""
    return open("/dev/tty", "rb", buffering=0)


def _read_key(tty_fd, timeout: float = 0.05) -> str:
    """
    Read one key from an already-open /dev/tty file descriptor.
    Uses termios raw mode + select so it never blocks longer than `timeout`.
    """
    fd = tty_fd.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([tty_fd], [], [], timeout)
        if rlist:
            ch = tty_fd.read(1).decode("latin-1")
            # Swallow escape sequences (arrow keys, F-keys …)
            if ch == "\x1b":
                try:
                    while True:
                        r, _, _ = select.select([tty_fd], [], [], 0.01)
                        if r:
                            tty_fd.read(1)
                        else:
                            break
                except Exception:
                    pass
                return ""
            return ch
        return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


class KeyboardJointTeleop(KeyboardTeleop):
    """
    Keyboard teleoperation for joint-space control.

    Reads keys via /dev/tty (termios) so it works whether stdin is a real
    terminal, a pipe, or a heredoc — no X11 / display required.

    Key layout
    ----------
    Joint 1 : Q / A      Joint 5 : T / G
    Joint 2 : W / S      Joint 6 : Y / H
    Joint 3 : E / D      Joint 7 : U / J  (Gen3 only)
    Joint 4 : R / F
    Gripper  : O (close) / L (open)
    Quit     : Ctrl+C
    """

    config_class = KeyboardJointTeleopConfig
    name = "keyboard_joint"

    def __init__(self, config: KeyboardJointTeleopConfig):
        super().__init__(config)
        self.config = config

        self.misc_keys_queue: Queue[Any] = Queue()
        self.curr_joint_actions: dict[str, float] = {
            key: 0.0 for key in self.config.arm_action_keys
        }
        if self.config.gripper_action_key:
            self.curr_joint_actions[self.config.gripper_action_key] = 0.0

        self._pressed_keys: set[str] = set()
        self._key_lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._tty_file = None
        self._running = False
        self._is_connected = False

        logger.info(f"KeyboardJointTeleop initialized with keys: {self.config.arm_action_keys}")
        logger.info(f"Gripper key: {self.config.gripper_action_key}")

    # ------------------------------------------------------------------
    # Override is_connected as read/write property (base is read-only)
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @is_connected.setter
    def is_connected(self, value: bool) -> None:
        self._is_connected = value

    # ------------------------------------------------------------------
    # Key reader thread — uses /dev/tty, never sys.stdin
    # ------------------------------------------------------------------

    def _key_reader_loop(self) -> None:
        print(
            "\n[KeyboardJointTeleop] Key controls:\n"
            "  Joint 1: Q/A   Joint 2: W/S   Joint 3: E/D\n"
            "  Joint 4: R/F   Joint 5: T/G   Joint 6: Y/H\n"
            "  Joint 7: U/J   Gripper: O(close)/L(open)\n"
            "  Ctrl+C to quit\n",
            flush=True,
        )
        try:
            self._tty_file = _open_tty()
        except OSError as e:
            logger.error(f"Cannot open /dev/tty: {e}. Keyboard input disabled.")
            return

        try:
            while self._running:
                key = _read_key(self._tty_file, timeout=0.05)
                if key == "\x03":  # Ctrl+C
                    os.kill(os.getpid(), 2)  # SIGINT
                    break
                with self._key_lock:
                    if key:
                        self._pressed_keys.add(key.lower())
                    else:
                        self._pressed_keys.clear()
        finally:
            try:
                self._tty_file.close()
            except Exception:
                pass
            self._tty_file = None

    # ------------------------------------------------------------------
    # Teleoperator interface
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Start background key reader; bypasses pynput from base class."""
        self._is_connected = True
        self._running = True
        self._reader_thread = threading.Thread(
            target=self._key_reader_loop, daemon=True
        )
        self._reader_thread.start()

    def disconnect(self) -> None:
        self._running = False
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)
            self._reader_thread = None
        self._is_connected = False

    @property
    def action_features(self) -> dict:
        n_joints = len(self.config.arm_action_keys)
        action_names = self.config.arm_action_keys.copy()
        if self.config.gripper_action_key:
            n_joints += 1
            action_names.append(self.config.gripper_action_key)
        return {
            "dtype": "float32",
            "shape": (n_joints,),
            "names": dict.fromkeys(action_names, float),
        }

    def get_action(self) -> dict[str, Any]:
        """Return current joint actions based on currently pressed keys."""
        if not self._is_connected:
            raise DeviceNotConnectedError(
                "KeyboardJointTeleop is not connected. Call connect() first."
            )

        with self._key_lock:
            pressed = set(self._pressed_keys)

        if pressed:
            logger.debug(f"Pressed keys: {pressed}")

        for key_str, (joint_index, direction) in KEY_MAPPINGS.items():
            if joint_index >= len(self.config.arm_action_keys):
                continue
            if key_str in pressed:
                joint_key = self.config.arm_action_keys[joint_index]
                increment = direction * self.config.action_increment
                self.curr_joint_actions[joint_key] += increment
                logger.debug(f"Moving {joint_key} by {increment:+.4f} (key: {key_str})")

        if self.config.gripper_action_key:
            for key_str, direction in GRIPPER_KEYS.items():
                if key_str in pressed:
                    self.curr_joint_actions[self.config.gripper_action_key] += (
                        direction * self.config.action_increment
                    )
            self.curr_joint_actions[self.config.gripper_action_key] = max(
                0.0, min(1.0, self.curr_joint_actions[self.config.gripper_action_key])
            )

        return self.curr_joint_actions.copy()

    def get_misc_key(self) -> Any | None:
        if self.misc_keys_queue.empty():
            return None
        return self.misc_keys_queue.get_nowait()
