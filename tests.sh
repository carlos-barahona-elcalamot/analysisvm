
check_users="root/Asdqwe!23 alumno/Asdqwe!23"


checkuser() {

    usr=$1
    psw=$2

    echo "         {"
    
    ls /home/$usr > /dev/null 2>&1 &&  echo "         \"usr_home\": 1," || echo "         \"usr_home\": 0,"


    sys_pswd_hash=$( cat /etc/shadow | grep $usr | { IFS=: read usr hash resto; echo $hash ; } ) 
    # echo "Password hash=$sys_pswd_hash"
    if [ ! -z $sys_pswd_hash ]; then
        alg=$( echo $sys_pswd_hash | { IFS=$ read a a alg salt hash; echo $alg ; } )
        salt=$( echo $sys_pswd_hash | { IFS=$ read x alg a salt hash; echo \$$alg\$$a\$$salt\$; } )

        # echo "Parameters: alg=$alg salt=$salt"
        # if [[ $sys_pswd_hash == $(echo "$psw" | openssl passwd -$alg -salt $salt -stdin ) ]] ; then
	    # python3 -c "import crypt; print(crypt.crypt('$psw','$salt'))"
        if [[ $sys_pswd_hash == $( python3 -c "import crypt; print(crypt.crypt('$psw','$salt'))" ) ]] ; then
            echo "         \"usr_password\": 1"
        else
            echo "         \"usr_password\": 0"
        fi
    fi

    echo "         },"
}

es_tiny=0
es_alpine=0
es_debian=0
spanish_keyboard=0
spanish_time=0
uname -a | grep -q tinycore && es_tiny=1
uname -a | grep -q Alpine && es_alpine=1
uname -a | grep -q Debian && es_debian=1

if [ $es_tiny -eq 1 ]; then
    distribution="tiny"
elif [ $es_alpine -eq 1 ]; then
    distribution="alpine"
elif [ $es_debian -eq 1 ]; then
    distribution="debian"
else
    distribution="linux"
fi


if [ $es_tiny -eq 0 ]; then 
    root_dev=$( mount | grep -Eoe '/dev/[a-zA-Z0-9]* on / .*' | cut -d ' ' -f 1 )
    opt_dev=$( mount | grep -Eoe '/dev/[a-zA-Z0-9]* on /opt .*' | cut -d ' ' -f 1 )
    home_dev=$( mount | grep -Eoe '/dev/[a-zA-Z0-9]* on /home .*' | cut -d ' ' -f 1 )

    ls /etc/keymap | grep -qEe '\<es.*gz' && spanish_keyboard=1
fi

date | grep -qEe '\<CET\>' && spanish_time=1

check_users_result=$( for usrpsw in $check_users; do echo "$usrpsw" | (IFS=/ read usr psw; echo "      \"$usr\" : "; checkuser "$usr" "$psw"); done )
# Remove trailing ,
check_users_result=${check_users_result::-1}

root_data=$( df -T / | tail -1 | { read dev fs size used rest ; echo "      \"dev\" : \"$dev\","; echo "      \"fs\" : \"$fs\","; echo "      \"size\" : $size,"; echo "      \"used\" : $used";  } )
home_data=$( df -T /home | tail -1 | { read dev fs size used rest ; echo "      \"dev\" : \"$dev\","; echo "      \"fs\" : \"$fs\","; echo "      \"size\" : $size,"; echo "      \"used\" : $used";  } )
opt_data=$( df -T /opt | tail -1 | { read dev fs size used rest ; echo "      \"dev\" : \"$dev\","; echo "      \"fs\" : \"$fs\","; echo "      \"size\" : $size,"; echo "      \"used\" : $used";  } )
efi_data=$( df -T /boot/efi | tail -1 | { read dev fs size used rest ; echo "      \"dev\" : \"$dev\","; echo "      \"fs\" : \"$fs\","; echo "      \"size\" : $size,"; echo "      \"used\" : $used";  } )

# echo " " > /dev/ttyS0
# echo "root_dev=$root_dev " > /dev/ttyS0
# echo "home_dev=$home_dev " > /dev/ttyS0
# echo "opt_dev=$opt_dev " > /dev/ttyS0
# echo "es_tiny=$es_tiny " > /dev/ttyS0
# echo "es_alpine=$es_alpine " > /dev/ttyS0
# echo "spanish_kbd=$spanish_keyboard " > /dev/ttyS0
# echo "spanish_time=$spanish_time " > /dev/ttyS0
# echo "developer_home=$developer_home " > /dev/ttyS0
# echo "developer_passwd=$developer_passwd " > /dev/ttyS0
# echo " root_dev=$root_dev home_dev=$home_dev opt_dev=$opt_dev es_tiny=$es_tiny es_alpine=$es_alpine spanish_kbd=$spanish_keyboard spanish_time=$spanish_time developer_home=$developer_home developer_passwd=$developer_passwd " 

echo "{" | tee /dev/ttyS0
echo "   \"root_dev\" : \"$root_dev\"," | tee /dev/ttyS0
echo "   \"home_dev\" : \"$home_dev\"," | tee /dev/ttyS0
echo "   \"opt_dev\" : \"$opt_dev\"," | tee /dev/ttyS0
echo "   \"es_tiny\" : $es_tiny," | tee /dev/ttyS0
echo "   \"es_alpine\" : $es_alpine," | tee /dev/ttyS0
echo "   \"es_debian\" : $es_debian," | tee /dev/ttyS0
echo "   \"distribution\" : $distribution," tee /dev/ttyS0
echo "   \"spanish_kbd\" : $spanish_keyboard," | tee /dev/ttyS0
echo "   \"spanish_time\" : $spanish_time," | tee /dev/ttyS0
echo "   \"users\" : { " | tee /dev/ttyS0
echo "$check_users_result" | tee /dev/ttyS0
echo "   }, " | tee /dev/ttyS0
#echo "   \"developer_home\" : $developer_home," | tee /dev/ttyS0
#echo "   \"developer_passwd\" : $developer_passwd," | tee /dev/ttyS0
echo "   \"root_data\" : {" | tee /dev/ttyS0
echo "$root_data" | tee /dev/ttyS0
echo "   },"  | tee /dev/ttyS0
echo "   \"home_data\" : {" | tee /dev/ttyS0
echo "$home_data" | tee /dev/ttyS0
echo "   },"  | tee /dev/ttyS0
echo "   \"opt_data\" : {" | tee /dev/ttyS0
echo "$opt_data" | tee /dev/ttyS0
echo "   },"  | tee /dev/ttyS0
echo "   \"efi_data\" : {" | tee /dev/ttyS0
echo "$efi_data" | tee /dev/ttyS0
echo "   }"  | tee /dev/ttyS0
echo "}" | tee /dev/ttyS0

# sleep 3 # wait for serial port to transmit all data
# read  -p "Enter:" mainmenuinput

# if [ $es_tiny -eq 1 ]; then sudo poweroff 
# else poweroff
# fi
