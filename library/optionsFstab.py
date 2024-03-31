#!/usr/bin/python3
# Basé sur la doc Ansible :
# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: optionsFstab

short_description: Manage options in existing fstab records

version_added: "1.0.0"

description: Manage options in existing fstab records

options:
    path:
        description: 
            - The mount point of the entry to work with
            - if this path is not found in fstab, no change will be made, and no error either
        required: true
        type: str

    options:
        description:
            - list of options with modifiers +, -
            - Parameter description can be a list as well.
        required: true
        type: str

    backup:
        description:
            - filename of backup to create       
            - no backup if absent
            - use only in the first use of module in a playbook
        required: false
        type: str

    fstab:
        description: 
            - complete path and filename of fstab to work with
            - default to /etc/fstab
        required: false
        type: str
        
author:
    - Bertrand Maujean
'''

EXAMPLES = r'''
- name: options de montage sur un point de montage
  optionsFstab:
    path: /var
    options: "+nodev -noauto +nosuid +truc=bidule"

- name: options de montage sur plusieurs points de montages
  optionsFstab:
     - path: /var
       options: "+nodev -noauto +nosuid +truc=bidule"
     - path: /usr
       options: "-nosuid"

'''

RETURN = r'''
message:
    description: The output message that the test module generates.
    type: str
    returned: always
    sample:
     - <class 'PermissionError'> when opening for write /etc/fstab
     - <class 'FileNotFoundError'> when opening for read /etc/fstabxx
     - /varx not found in fstab file /etc/fstab, nothing done
     
'''

from ansible.module_utils.basic import AnsibleModule


result_message = ""
nbChangements  = 0

def run_module():
    module_args = dict(
        path    = dict(type='str', required=True),
        options = dict(type='str', required=True),
        fstab   = dict(type='str', required=False, default="/etc/fstab"),
        backup  = dict(type='str', required=False, default=None)
    )
    result = dict(
        changed=False,
        original_message='',
        message=''
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    r = traiteFstab(module.params)
    result["message"] = result_message
    
    if nbChangements >0: result["changed"] = True

    if r:
        module.exit_json(**result)
    else:
        module.fail_json(msg='erreur', **result)

    return


def traiteChaineOptions(chaineOptions, module_args):
    global result_message, nbChangements

    # Décompose la chaine d'options existantes en dict
    options  = chaineOptions.split(',')
    options2 = {}
    for o in options:
        o = o.split("=")
        o2 = {}
        if len(o) == 1:
            o2 = { o[0]: None }
        elif len(o) == 2:
            o2 = { o[0]: o[1] }
        else:
            result_message = "Option non comprise, ne fait rien "+str(o)
            return None
        
        options2.update(o2)

    # Décompose la chaine modificative reçue via Ansible
    changements  = module_args["options"].split()
    changements2 = []
    for c in changements:
        c2 = {}
        if c.startswith("+"):
            c2["action"] = "+"
            c3 = c[1:]
        elif c.startswith("-"):
            c2["action"] = "-"
            c3 = c[1:]
        else:
            c3 = c

        c3 = c3.split("=")
        if len(c3) == 1:
            c2["key"]   = c3[0]
            c2["value"] = None
        elif len(c3) == 2:
            c2["key"]   = c3[0]
            c2["value"] = c3[1]
        else:
            result_message = "Changement non compris, ne fait rien "+str(c3)
            return None

        changements2.append(c2)

    # Applique la chaine modificative
    for l in range(len(changements2)): # changement in changements2:
        changement = changements2[l]
        if changement["key"] in options2.keys():
            if changement["action"] == "+":
                # Remplace
                options2.update({ changement["key"]: changement["value"] })
            else:
                # Supprime
                options2.pop(changement["key"])
            pass 

        else:
            # Ajoute
            options2.update({ changement["key"]: changement["value"] })
        pass 

    # Et renvoie le résultat
    result = ""
    for k in options2.keys():
        result = result+k
        if options2[k] != None:
            result = result+"="+options2[k]
        result = result+","

    result = result[:-1] # enlève , finale
    return result


def traiteFstab(module_args):
    global result_message, nbChangements
    cheminFstab   = module_args["fstab"]
    cheminBackup  = module_args["backup"]

    # Lecture fichier d'entrée
    try:
        fichierIn = open(cheminFstab, "rt")
    except (OSError, PermissionError, FileNotFoundError) as e:
        result_message = "{:s} when opening for read {:s}".format(str(type(e)), str(cheminFstab))
        return False

    texte     = fichierIn.readlines()
    fichierIn.close()

    # Y aura-t-il un backup à créer ?
    if cheminBackup:
        try:
            fichierBak = open(cheminBackup, "wt")
        except (OSError, PermissionError, FileNotFoundError) as e:
            result_message = "{:s} when opening for write {:s}".format(str(type(e)), str(cheminBackup))
            return False

        fichierBak.writelines(texte) # les \n ont été laissés par readlines() avant
        fichierBak.close()

    changement = False # Avons nous rencontré la ligne recherchée ?
    for l in range(len(texte)): # ligne in texte:
        ligne = texte[l]

        # traite le cas commentaire
        c = ligne.strip()
        if c.startswith("#"): continue
        if c == "": continue

        # Décompose une entrée et vérifie qu'elle est valable
        dec = c.split()
        if len(dec) != 6: 
            result_message = "parse error in fstab line {:d} {:s}".format(dec, l)
            return False
        
        try:
            i = int(dec[4])
            i = int(dec[5])
        except ValueError:
            continue

        # est-ce l'entrée qu'on doit manipuler ?
        if module_args["path"] == dec[1]: 
            r = traiteChaineOptions(dec[3], module_args)
            if r:
                dec[3] = r
                changement = True
                ligne = ""
                for i in range(6):
                    ligne = ligne+str(dec[i])
                    if i!=6: ligne = ligne+"\t"

                ligne = ligne+"\n" # writelines() ne le met pas lui même
                texte[l] = ligne
                nbChangements += 1
                break # Ne cherche pas d'autre entrée dans ce fstab
            else:
                # cas d'erreur au traitement de la chaine d'options
                return False # Quitte vers erreur
            
    if nbChangements == 0:
        result_message = "{:s} not found in fstab file {:s}, nothing done".format(module_args["path"], cheminFstab)
        return True # Quitte mais sans erreur pour autant
    

    try:
        fichierOut = open(cheminFstab, "wt")
    except (OSError, PermissionError, FileNotFoundError) as e:
        result_message = "{:s} when opening for write {:s}".format(str(type(e)), str(cheminFstab))
        return False
   

    fichierOut.writelines(texte)
    fichierOut.close()
    return True

def main():
    run_module()

if __name__ == '__main__':
    main()