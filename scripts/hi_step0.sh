#!/bin/sh
# Step 0: read-only inventory of a Creality Hi before installing Kalico.
#
# Run ON THE PRINTER (busybox ash). It only reads: no file outside /tmp is
# written, no service is touched, nothing is sent to the MCUs.
# Serial numbers and MAC addresses are masked; IP addresses are not read.
#
#   sh /tmp/hi_step0.sh [/tmp/c_helper.so] > /tmp/step0.txt 2>&1
#
# With a c_helper.so path (and chelper_load.py next to this script) it also
# checks that the cross-compiled library loads with the printer's glibc.
# Expected values: docs/phase1-plan.md, section "Paso 0".

HERE=$(cd "$(dirname "$0")" && pwd)
CHELPER=$1

sec() { echo; echo "=== $1"; }
mask() { sed -E 's/(serialno|sn|mac|ethaddr|wifiaddr|bt_mac|uuid|did|key|token|password|passwd)=[^ ]*/\1=<masked>/Ig'; }
have() { command -v "$1" >/dev/null 2>&1; }

sec "01 identity"
echo "model=$(get_sn_mac.sh model 2>/dev/null)"
echo "board=$(get_sn_mac.sh board 2>/dev/null)"
echo "fw_version=$(fw_printenv -n version 2>/dev/null)"
grep -E "DISTRIB_(INFO|TARGET|ARCH)|TINA_VERSION" /etc/openwrt_release 2>/dev/null
uname -a

sec "02 boot slot (U-Boot environment, read with fw_printenv)"
for v in boot_partition root_partition swu_mode swu_next swu_software swu_version parts_clean bootdelay; do
    echo "$v=$(fw_printenv -n $v 2>/dev/null)"
done
echo "--- variable names"
fw_printenv 2>/dev/null | cut -d= -f1 | tr '\n' ' '; echo
echo "--- boot logic variables"
fw_printenv 2>/dev/null | grep -E "^(bootcmd|boot_normal|boot_recovery|boot_fastboot|setargs_[a-z]*|bootlimit|bootcount|upgrade_available|altbootcmd|mmc_root|nand_root|root_partition|boot_partition|partitions)=" | mask
echo "--- /proc/cmdline"
mask < /proc/cmdline

sec "03 partitions"
ls -l /dev/by-name/ 2>/dev/null | awk '{print $9, $10, $11}'
echo "--- /proc/mtd"; cat /proc/mtd 2>/dev/null
echo "--- ubi volumes"
if have ubinfo; then ubinfo -a 2>/dev/null | grep -E "^(Volume ID|Name|Size|Type)"; fi
echo "--- /proc/partitions"; cat /proc/partitions

sec "04 mounts and space"
mount
echo "--- df"; df -h 2>/dev/null
echo "--- df -k /mnt/UDISK"; df -k /mnt/UDISK | tail -1
echo "--- memory"; free 2>/dev/null

sec "05 overlay (changes made on top of the read-only rootfs)"
ls -la /overlay 2>/dev/null
for d in /overlay/upper /overlay; do
    [ -d "$d/etc" ] && { echo "--- $d (depth 3, first 80)"; find "$d" -maxdepth 3 2>/dev/null | grep -v -E "dropbear|shadow|passwd|wpa|wifi|cert|key" | head -80; break; }
done
echo "--- stock service scripts changed in the overlay"
for f in klipper klipper_mcu moonraker app mcu_update; do
    for d in /overlay/upper /overlay; do
        [ -e "$d/etc/init.d/$f" ] && echo "MODIFIED: $d/etc/init.d/$f"
    done
done
echo "(no MODIFIED line = stock scripts)"

sec "06 cpu"
grep -E "^(model name|Features|CPU (implementer|architecture|variant|part|revision)|Hardware)" /proc/cpuinfo | sort -u
echo "cores=$(grep -c ^processor /proc/cpuinfo)"
cat /proc/loadavg

sec "07 libc"
ls -l /lib/libc.so.6 /lib/ld-linux-armhf.so.3 /lib/libpthread.so.0 /lib/libm.so.6 /usr/lib/libffi.so.* 2>&1

sec "08 python"
for p in /usr/bin/python3 /usr/share/klippy-env/bin/python; do
    echo "--- $p"; ls -l $p 2>&1
    $p - <<'PYEOF' 2>&1
import sys, platform
print("python", sys.version.replace("\n", " "))
print("machine", platform.machine(), "libc", platform.libc_ver())
print("prefix", sys.prefix, "base_prefix", sys.base_prefix)
for name in ("zlib", "ctypes", "ssl", "sqlite3", "multiprocessing", "termios",
             "fcntl", "select", "json", "queue", "importlib.metadata",
             "cffi", "greenlet", "jinja2", "markupsafe", "serial", "numpy",
             "can", "tornado"):
    try:
        mod = __import__(name, fromlist=["x"])
        print("ok  ", name, getattr(mod, "__version__", getattr(mod, "VERSION", "")))
    except Exception as e:
        print("FAIL", name, type(e).__name__, e)
import select
print("select.poll", hasattr(select, "poll"), "epoll", hasattr(select, "epoll"))
import os
print("os.sched_setaffinity", hasattr(os, "sched_setaffinity"))
PYEOF
done

sec "09 tools"
for t in git gcc tar gzip gunzip sha256sum md5sum wget curl nohup setsid start-stop-daemon stty flock rsync timeout unsquashfs mksquashfs ubiupdatevol ubinfo fw_printenv fw_setenv swupdate strace scp mcu_util; do
    printf "%-18s %s\n" "$t" "$(command -v $t 2>/dev/null || echo -)"
done
echo "--- busybox tar"; tar --help 2>&1 | head -12

sec "10 services"
ls /etc/rc.d/ | tr '\n' ' '; echo
echo "--- processes"
ps w 2>/dev/null | grep -E "klippy|klipper_mcu|moonraker|-server|Monitor|nginx|webrtc|cam_app" | grep -v grep | awk '{$1="";$2="";$3="";$4=""; print}' | mask

sec "11 mcu"
ls -l /dev/ttyS* 2>&1 | awk '{print $1, $3, $4, $5, $6, $NF}'
echo "--- /tmp/.mcu_version"; cat /tmp/.mcu_version 2>/dev/null; echo
echo "--- /tmp/mcu_update.log (last 25)"; tail -25 /tmp/mcu_update.log 2>/dev/null

sec "12 stock klippy baseline"
LOG=/mnt/UDISK/printer_data/logs/klippy.log
ls -l $LOG 2>&1 | awk '{print $5, $6, $7, $8, $9}'
grep -E "^(Git version|CPU|Python|Args):" $LOG 2>/dev/null | tail -4
echo "--- last Stats line (load and serial error counters)"
grep "^Stats " $LOG 2>/dev/null | tail -1 | cut -c1-900
echo "--- config files"; ls -l /mnt/UDISK/printer_data/config/ 2>/dev/null | awk '{print $5, $9}'
echo "--- existing kalico-hi install"; ls -la /mnt/UDISK/kalico-hi 2>&1 | head -12

sec "13 c_helper.so load test"
if [ -n "$CHELPER" ] && [ -f "$CHELPER" ] && [ -f "$HERE/chelper_load.py" ]; then
    sha256sum "$CHELPER"
    python3 "$HERE/chelper_load.py" "$CHELPER" 2>&1
else
    echo "skipped (usage: hi_step0.sh /tmp/c_helper.so, with chelper_load.py next to this script)"
fi

sec "end"
