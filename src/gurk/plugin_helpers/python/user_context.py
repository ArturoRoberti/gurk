import grp
import os
import subprocess


class UserContext:
    """Temporarily drop privileges to the user who invoked sudo."""

    def __enter__(self):
        sudo_user = os.environ.get("SUDO_USER")
        if not sudo_user:
            self.active = False
            return self

        self.active = True
        self.orig_euid = os.geteuid()
        self.orig_egid = os.getegid()
        self.orig_groups = os.getgroups()
        # os.umask() sets the new mask and returns the previous one —
        # this is the only way to read the umask without a dedicated syscall.
        self.orig_umask = os.umask(0)
        os.umask(self.orig_umask)

        uid = int(os.environ["SUDO_UID"])
        gid = int(os.environ["SUDO_GID"])

        groups = [
            g.gr_gid
            for g in grp.getgrall()
            if sudo_user in g.gr_mem or g.gr_gid == gid
        ]

        # Get umask while still root (before privilege drop), using a login
        # shell so the user's profile is sourced and their umask is returned.
        user_umask = self.get_user_umask(sudo_user)

        # Drop privileges: GID and groups first, EUID last.
        os.setegid(gid)
        os.setgroups(groups)
        os.seteuid(uid)
        os.umask(user_umask)

        return self

    def __exit__(self, exc_type, exc, tb):
        if not self.active:
            return

        # Restore EUID first (back to root) so we can restore GID and groups.
        os.seteuid(self.orig_euid)
        os.setegid(self.orig_egid)
        os.setgroups(self.orig_groups)
        os.umask(self.orig_umask)

    @staticmethod
    def get_user_umask(sudo_user: str, default: int = 0o022) -> int:
        """
        Get the umask of the specified user by running a login shell command.

        :param sudo_user: The username to get the umask for
        :type sudo_user: str
        :param default: The default umask to return if retrieval fails
        :type default: int
        :return: The umask of the specified user, or the default if retrieval fails
        :rtype: int
        """
        try:
            result = subprocess.run(
                ["sudo", "-u", sudo_user, "bash", "-l", "-c", "umask"],
                capture_output=True,
                text=True,
                check=True,
            )
            return int(result.stdout.strip(), 8)
        except Exception:
            return default
