# Analysis VirtualBox VM
## Components
- `run_analysis.py`: python script. This is the main script to run analysis.
- `analysis-partitions` : bash script. This is the script for the --hdd analysis. It runs on AnalysisVM and analyzes partitions on /dev/sdb.
- `tests.sh`: bash script with tests to be run inside students VM. The `run_analysis.py --hdd` command copies this script to each partition of the student VM as part of the tests.
- `repair_vbox_efi`: bash script. This script is run as a part of --hdd option when an efi partition is detected. It corrects the missconfiguration of VirtualBox EFI when a machine is exported and then imported as ova.
- `analysisVM/analysisvm`: private key to connect passwordless to AnalisisVMs virtual machine.

## Default setup environment
1. Install python lib [vboxapi](https://pypi.org/project/pyvbox/)
1. Download all scripts and resources to a folder.
2. Import analisisvm.ova into VirtualBox. This VM will login automatically as root when started. In case you need it, root password is *Asdqwe!23*
3. Configure the *analisisvm* network so you can access it through ssh. For example, if you use NAT networking (default), map local port 2200 to vm machine port 22, so you can connect with `ssh -p 2200 root@localhost` from your host machine.
4. cd to the installation folder and check that you can connect to AnalisisVMs machine using `ssh -i analysisVM/analysisvm root@localhost` whithout being asked for a password.
6. Prepare a CSV file with the list of students, and at least, the following 3 columns: 'First name', 'Surname' and 'Email address' (you can get this file directly from Moodle: Grades -> Export (plain text file) and unselect all fields). Put this file in the *data* folder and rename it to *students.csv*.
7. Download student machines to data/submissions folder (this folder should contain only ova files from students you want to analyze). You should require students to name their ova files and machines as their moodle e-mail without the server part (example: name.surname@server.com -> name.surname.ova ), so that the script can assign each machine to the student automatically.
8. The folder *data/imported/* will contain imported virtual machines when you run the script with the `--import-ova' option.

See script help ( `./run_analysis.py --help` ) to see options to customize your environment if you don't want to use the defaults.

## First steps
### Assign ova submitted files to students and generate *records.json* file

`> ./run_analysis.py -a`

This command will try to assign each file in the *data/submissions/* folder to a student in the *data/students.csv* file. OVA files that couldn't get assigned will be assigned interactively by the user: the scrit will show a list of possible students and the file that have to be assigned, the user will select the correct student.
Once the assignment has finished, a *records.json* will be generated in the data folder. This file contains info about students and their ova file submitted.

### Import ova files to VirtualBox
`> ./run_analysis.py --import-ova`

This command will import ova files assigned to students into VirtualBox. By default, the virtual machines will be imported into a group named */AnalysisVM*, they will be named *Ana_{student_id}* (where *student_id* is the student email without the server part) and they will be stored into the *data/imported/* folder.