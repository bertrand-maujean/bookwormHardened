# boorkwormHardened
Small Ansible Playbook to harden a Debian 12 Ansible according to 
- CIS
- https://cyber.gouv.fr/sites/default/files/document/fr_np_linux_configuration-v2.0.pdf

Should raise CIS score to at least than 65%.
I check CIS compliance using Wazuh, and lots of tests are failed due to incorrect or incomplete testing rules. For example, includes in conf files are not recursively processed.

## Issues
Can not work with applications that strictly follow the hardening rules, in particular application which assume an executable /tmp or /var
(It's the case with Wazuh agent, whose binaries lives in /var... lol )

## Files
step3.yml is the playbook
Come along with other ancillary files 

## Licence
Distributed under  GPLv3 https://www.gnu.org/licenses/gpl-3.0.en.html




