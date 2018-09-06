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

from __future__ import absolute_import
import os
import subprocess
import tempfile
import logging
import pexpect
import six


class SSHControllerException(Exception):
    pass


class SSHController(object):
    """
    SSH controller class for common SSH operations
    """

    RSA_KEY_SIZE = 2048
    DEFAULT_SSH_PORT = 22
    SSH_COMMAND = 'ssh'
    SSH_KEYGEN_COMMAND = 'ssh-keygen'
    SSH_KEYSCAN_COMMAND = 'ssh-keyscan'

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
                self.SSH_KEYGEN_COMMAND,
                '-b', six.text_type(key_size),
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
                self.SSH_KEYSCAN_COMMAND,
                '-p', six.text_type(port),
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
                self.SSH_KEYGEN_COMMAND,
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
        except Exception as e:
            raise SSHControllerException(
                'Error getting host key data: %s' % e)
        return self.get_fingerprint_from_key_data(key_data)

    def execute_remote_command(self, command, private_key_file, username, hostname, port=DEFAULT_SSH_PORT,
                               **kwargs):
        """
        Executes a program remotely
        """
        ssh_command_start = [
            self.SSH_COMMAND,
        ]
        ssh_command_end = [
            '%s@%s' % (username, hostname),
            '-p', six.text_type(port),
            command,
        ]

        ssh_command_start.extend(['-i', private_key_file])
        ssh_command_start.extend(
            ['-o', 'PreferredAuthentications=publickey'])
        ssh_command_start.extend(
            ['-o', 'PasswordAuthentication=no'])

        # Options
        for k, v in kwargs.items():
            ssh_command_start.extend(['-o', '%s=%s' % (k, six.text_type(v))])
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
                    local_host='127.0.0.1', **kwargs):
        """
        Open a tunnel with given ports and return SSH PID
        """
        ssh_command_start = [
            self.SSH_COMMAND,
        ]
        ssh_command_end = [
            '%s@%s' % (username, hostname),
            '-p', six.text_type(port),
            '-L', '%s:%s:%s:%s' % (local_host, local_port,
                                   tunnel_host, tunnel_port),
            '-N'
        ]

        ssh_command_start.extend(['-i', private_key_file])
        ssh_command_start.extend(
            ['-o', 'PreferredAuthentications=publickey'])
        ssh_command_start.extend(
            ['-o', 'PasswordAuthentication=no'])
        # Options
        for k, v in kwargs.items():
            ssh_command_start.extend(['-o', '%s=%s' % (k, six.text_type(v))])
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

    def install_pubkey(self, pub_key, username, password,
                       hostname, port=DEFAULT_SSH_PORT,
                       password_prompt='.*(P|p)assword:',
                       command_prompt='.+\$',
                       **kwargs):
        """
        Install a public key in a remote host
        """
        # Check that pub_key is a real public key by calculating fingerprint
        logging.debug('Verifying public key')
        fp = self.get_fingerprint_from_key_data(pub_key)
        logging.debug('Public key fingerprint: %s' % fp)
        try:
            # Open connection to given host and simulate a session
            ssh = pexpect.spawn('%s %s@%s -p %s' % (
                self.SSH_COMMAND,
                username,
                hostname,
                port
            ), env={'PATH': os.environ['PATH'], 'LANG': 'C'})

            def execute_command(command, final=False):
                logging.debug('Executing command: "%s"' % command)
                ssh.sendline(command)
                if not final:
                    ssh.expect(command_prompt)

            logging.debug('Waiting password prompt')
            prompts = [password_prompt, command_prompt]
            result = ssh.expect(prompts)
            if result == 0:
                logging.debug('Sending password')
                ssh.sendline(password)
                result = ssh.expect(prompts)
                if result == 0:
                    # Bad credentials
                    logging.debug(
                        'Password prompted again. Invalid credentials.')
                    raise SSHControllerException(
                        'Invalid credentials')

            execute_command('mkdir -p ~/.ssh/')
            execute_command('chmod 700 ~/.ssh/')
            execute_command('echo "%s" >> ~/.ssh/authorized_keys' % pub_key)
            execute_command('chmod 600 ~/.ssh/authorized_keys')
            execute_command('exit', final=True)
        except Exception as e:
            logging.error('Error installing SSH public key: %s' % e)
            raise SSHControllerException(
                'Error installing SSH public key: %s' % e)
