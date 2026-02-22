# Remount USB

Small helper to remount the USB device used for ISO storage (or any USB mount).

## Script
- `remount-usb.sh`

## Usage
```bash
./remount-usb.sh
./remount-usb.sh /mnt/usb-iso
./remount-usb.sh /mnt/usb-iso /dev/sdb1
./remount-usb.sh --kill /mnt/usb-iso /dev/sdb1
./remount-usb.sh --label usb-iso /mnt/usb-iso
```

## Notes
- If `DEVICE` is omitted, the script tries to detect the current device backing `MOUNTPOINT`.
- By default the script prefers the device with label `usb-iso`. If the current
  mount device differs from the label device, it will prompt you to choose.
- If the mount is not active, you must provide `DEVICE` or use `--label`.
- Use `--kill` to terminate processes holding the mount if unmount fails.
- Requires root; the script will re-run itself with `sudo` if available.

## Common Checks
```bash
mount | grep /mnt/usb-iso
findmnt -no SOURCE --target /mnt/usb-iso
ls -l /mnt/usb-iso
```

## Troubleshooting
- If unmount says `target is busy`, use `--kill` or stop the process holding the mount.
- If you see I/O errors, try a different USB port/cable and verify the ISO file checksum.
