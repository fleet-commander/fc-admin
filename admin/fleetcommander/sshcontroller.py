# -*- coding: utf-8 -*-
# vi:ts=4 sw=4 sts=4

# Copyright (C) 2015 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the licence, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# Authors: Alberto Ruiz <aruiz@redhat.com>
#          Oliver Gutiérrez <ogutierrez@redhat.com>

import os
import subprocess
import tempfile


class SSHControllerException(Exception):
    pass


class SSHController(object):
    """
    SSH controller class for common SSH operations
    """

    RSA_KEY_SIZE = 2048
    DEFAULT_SSH_PORT = 22

    def __init__(self):
        """
        Class initialization
        """
        pass

    def generate_ssh_keypair(self, private_key_file, key_size=RSA_KEY_SIZE):
        """
        Generates SSH private and public keys
        """
        prog = subprocess.Popen(
            [
                'ssh-keygen',
                '-b', unicode(key_size),
                '-t', 'rsa',
                '-f', private_key_file,
                '-q',
                '-N', ''
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, error = prog.communicate()
        if prog.returncode != 0:
            raise SSHControllerException(
                'Error generating keypair: %s' % error)

    def scan_host_keys(self, hostname, port=DEFAULT_SSH_PORT):
        prog = subprocess.Popen(
            [
                'ssh-keyscan',
                '-p', unicode(port),
                hostname,
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, error = prog.communicate()
        prog.wait()
        if prog.returncode == 0:
            return out
        else:
            raise SSHControllerException(
                'Error getting host keys: %s' % error)

    def add_keys_to_known_hosts(self, known_hosts_file, key_data):
        # First create path if does not exists
        directory = os.path.dirname(known_hosts_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(known_hosts_file, 'a') as fd:
            fd.write(key_data)
            fd.close()

    def add_to_known_hosts(self, known_hosts_file, hostname, port=DEFAULT_SSH_PORT):
        key_data = self.scan_host_keys(hostname, port)
        self.add_keys_to_known_hosts(known_hosts_file, key_data)

    def check_known_host(self, known_hosts_file, hostname):
        """
        Checks if a host is in given known hosts file
        """
        if os.path.exists(known_hosts_file):
            # Check if host exists in file
            with open(known_hosts_file) as fd:
                lines = fd.readlines()
                fd.close()
            for line in lines:
                hosts, keytype, key = line.split()
                if hostname in hosts.split(','):
                    return True
        return False

    def get_fingerprint_from_key_data(self, key_data):
        """
        Get host SSH fingerprint
        """
        tmpfile = tempfile.mktemp(prefix='fc-ssh-keydata')
        with open(tmpfile, 'w') as fd:
            fd.write(key_data)
            fd.close()
        prog = subprocess.Popen(
            [
                'ssh-keygen',
                '-l',
                '-f', tmpfile,
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, error = prog.communicate()
        prog.wait()
        os.remove(tmpfile)
        if prog.returncode == 0:
            return out
        else:
            raise SSHControllerException(
                'Error generating fingerprint from key data: %s' % error)

    def get_host_fingerprint(self, hostname, port=DEFAULT_SSH_PORT):
        """
        Get host SSH fingerprint
        """
        try:
            key_data = self.scan_host_keys(hostname, port)
        except Exception, e:
            raise SSHControllerException(
                'Error getting host key data: %s' % e)
        return self.get_fingerprint_from_key_data(key_data)

    def execute_remote_command(self, command, private_key_file, username, hostname, port=DEFAULT_SSH_PORT,
                               **kwargs):
        """
        Executes a program remotely
        """
        ssh_command_start = [
            'ssh',
        ]
        ssh_command_end = [
            '%s@%s' % (username, hostname),
            '-p', unicode(port),
            command,
        ]

        ssh_command_start.extend(['-i', private_key_file])
        ssh_command_start.extend(
            ['-o', 'PreferredAuthentications=publickey'])
        ssh_command_start.extend(
            ['-o', 'PasswordAuthentication=no'])

        # Options
        for k, v in kwargs.items():
            ssh_command_start.extend(['-o', '%s=%s' % (k, unicode(v))])
        ssh_command_start.extend(ssh_command_end)
        # Execute command
        prog = subprocess.Popen(
            ssh_command_start, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, error = prog.communicate()
        if prog.returncode == 0:
            return out
        else:
            raise SSHControllerException(
                'Error executing remote command: %s' % error)

    def open_tunnel(self, local_port, tunnel_host, tunnel_port,
                    private_key_file, username, hostname, port=DEFAULT_SSH_PORT,
                    **kwargs):
        """
        Open a tunnel with given ports and return SSH PID
        """
        ssh_command_start = [
            'ssh',
        ]
        ssh_command_end = [
            '%s@%s' % (username, hostname),
            '-p', unicode(port),
            '-L', '%s:%s:%s' % (local_port, tunnel_host, tunnel_port),
            '-N'
        ]

        ssh_command_start.extend(['-i', private_key_file])
        ssh_command_start.extend(
            ['-o', 'PreferredAuthentications=publickey'])
        ssh_command_start.extend(
            ['-o', 'PasswordAuthentication=no'])
        # Options
        for k, v in kwargs.items():
            ssh_command_start.extend(['-o', '%s=%s' % (k, unicode(v))])
        ssh_command_start.extend(ssh_command_end)

        # Execute SSH and bring up tunnel
        try:
            self._tunnel_prog = subprocess.Popen(
                ' '.join(ssh_command_start),
                shell=True)
            return self._tunnel_prog.pid
        except Exception as e:
            raise SSHControllerException(
                'Error opening tunnel: %s' % e)

    def install_pubkey(self, public_key_file, username, password,
                       hostname, port=DEFAULT_SSH_PORT, **kwargs):
        """
        Install a public key in a remote host

        Possible Options

        #!/usr/bin/expect
        eval spawn ssh -oStrictHostKeyChecking=no -oCheckHostIP=no usr@$myhost.example.com
        #use correct prompt
        set prompt ":|#|\\\$"
        interact -o -nobuffer -re $prompt return
        send "my_password\r"
        interact

        /usr/bin/expect -c 'expect "\n" { eval spawn ssh -oStrictHostKeyChecking=no -oCheckHostIP=no usr@$myhost.example.com; interact }
        """
        raise NotImplemented('Public key install is not ready yet!')
