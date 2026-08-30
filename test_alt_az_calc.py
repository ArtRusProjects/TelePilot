import dev_ctrl
import time
from machine import RTC





if __name__ == "__main__":
    dev = dev_ctrl.dev_ctrl(
        utc_offset=2,
        latitude=51.299,#49.68, 
        longitude=9.491,#8.62,
    )

    # ra = "10:51:41.8"
    # dec = "+08:13:06"

    #venus
    # ra = "13:11:59.43"
    # dec = "-10:56:58.6"

    ra = "14:50:40.45"
    dec = "+74:09:38.2"

    alt_old, az_old = dev.ra_dec_to_alt_az(ra, dec, apply_calibration=False)

    print(f"RA: {ra}, Dec: {dec} => Alt: {alt_old:.6f}, Az: {az_old:.6f}")

    while True:
        #print(dev.get_localtime())
        alt, az = dev.ra_dec_to_alt_az(ra, dec, apply_calibration=False)

        alt_diff = alt - alt_old
        az_diff = az - az_old

        #print(f"Alt: {alt:.6f}, Az: {az:.6f}, Alt diff: {alt_diff:.6f}, Az diff: {az_diff:.6f}")
        
        print(f"Alt: {dev_ctrl.decimal_to_degrees(alt)}, Az: {dev_ctrl.decimal_to_degrees(az)}")
        print(
            f"Alt-Diff: {dev_ctrl.decimal_to_degrees(alt_diff)}; "
            f"Az-Diff: {dev_ctrl.decimal_to_degrees(az_diff)}"
        )

        alt_old = alt
        az_old = az

        time.sleep(1)

    # ra_deg = dev_ctrl.ra_to_deg(ra)
    # dec_deg = dev_ctrl.dec_to_deg(dec)

    
    # ra_corr, dec_corr = dev_ctrl.precession_correction(
    #     ra_deg, dec_deg, 2026 - 2000
    # )