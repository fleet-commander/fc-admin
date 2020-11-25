#
# Copyright (C) 2020  FleetCommander Contributors see COPYING for license
#
"""Common tests' assumptions."""

SSH_TUNNEL_OPEN_PARMS = " ".join(
    [
        "{optional_args}",
        "-i",
        "{private_key_file}",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ControlMaster=yes",
        "-S",
        "{user_home}/.ssh/fc-control-ssh-tunnel.socket",
        "{username}@{hostname}",
        "-p",
        "{port}",
        "-L {local_forward}",
        "-N",
        "-f",
    ]
)

SSH_REMOTE_COMMAND_PARMS = " ".join(
    [
        "{optional_args}",
        "-i",
        "{private_key_file}",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "PasswordAuthentication=no",
        "{username}@{hostname}",
        "-p",
        "{port}",
        "{command}",
    ]
)
SSH_TUNNEL_CLOSE_PARMS = " ".join(
    [
        "{optional_args}",
        "-i",
        "{private_key_file}",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "PasswordAuthentication=no",
        "{username}@{hostname}",
        "-p",
        "{port}",
        "-S",
        "{user_home}/.ssh/fc-control-ssh-tunnel.socket",
        "-O",
        "exit",
    ]
)
