#include <math.h>

#include "py/objtuple.h"
#include "py/runtime.h"

#define GMST_PER_DAY 360.98564736629
#define DEG_TO_RAD (3.14159265358979323846 / 180.0)
#define RAD_TO_DEG (180.0 / 3.14159265358979323846)

static double normalize_degrees(double degrees) {
    degrees = fmod(degrees, 360.0);
    if (degrees < 0.0) {
        degrees += 360.0;
    }
    return degrees;
}

static double years_since_j2000(int year, int month, int day) {
    double julian_day =
        367.0 * year
        - (int)(7.0 * (year + (int)((month + 9) / 12)) / 4.0)
        + (int)(275.0 * month / 9.0)
        + day
        + 1721013.5;
    return (julian_day - 2451545.0) / 365.25;
}

static double gmst_simple(int year, int month, int day, double hour_utc) {
    double days =
        367.0 * year
        - (int)(7.0 * (year + (int)((month + 9) / 12)) / 4.0)
        + (int)(275.0 * month / 9.0)
        + day
        - 730531.5;
    days += hour_utc / 24.0;
    return normalize_degrees(280.46061837 + GMST_PER_DAY * days);
}

static mp_obj_t altaz_calculate(size_t n_args, const mp_obj_t *args) {
    (void)n_args;

    /*
     * Input:
     *   ra_deg      J2000 right ascension [deg]
     *   dec_deg     J2000 declination [deg]
     *   year/month/day
     *   hour/minute/second  local civil time
     *   latitude    geographic latitude [deg], north positive
     *   longitude   geographic longitude [deg], east positive
     *   utc_offset  local UTC offset [hours]
     *
     * Output:
     *   (GMST [deg], altitude [deg], azimuth [deg])
     *
     * Azimuth:
     *   0   = North
     *   90  = East
     *   180 = South
     *   270 = West
     */

    double ra_deg = mp_obj_get_float(args[0]);
    double dec_deg = mp_obj_get_float(args[1]);

    int year = mp_obj_get_int(args[2]);
    int month = mp_obj_get_int(args[3]);
    int day = mp_obj_get_int(args[4]);

    int hour = mp_obj_get_int(args[5]);
    int minute = mp_obj_get_int(args[6]);
    int second = mp_obj_get_int(args[7]);

    double latitude = mp_obj_get_float(args[8]);
    double longitude = mp_obj_get_float(args[9]);
    double utc_offset = mp_obj_get_float(args[10]);

    /*
     * ------------------------------------------------------------
     * 1. Time since J2000
     * ------------------------------------------------------------
     *
     * years = Julian years since J2000.0.
     */
    double years = years_since_j2000(year, month, day);

    /*
     * T is Julian centuries since J2000.0.
     * Required for the slow variation of the precession coefficients.
     */
    double T = years / 100.0;

    /*
     * ------------------------------------------------------------
     * 2. Precession from J2000.0 to date
     * ------------------------------------------------------------
     *
     * Approximate Meeus-style precession formula.
     *
     * m, n, nd are arcsec/year.
     */
    double m  = 3.07496 + 0.00186 * T;
    double n  = 1.33621 - 0.00057 * T;
    double nd = 20.0431 - 0.0085 * T;

    double ra_rad = ra_deg * DEG_TO_RAD;
    double dec_rad = dec_deg * DEG_TO_RAD;

    /*
     * Precession in arcseconds.
     */
    double dra_arcsec =
        (m + n * sin(ra_rad) * tan(dec_rad)) * years;

    double ddec_arcsec =
        nd * cos(ra_rad) * years;

    /*
     * Convert arcsec -> degrees.
     */
    ra_deg += dra_arcsec / 3600.0;
    dec_deg += ddec_arcsec / 3600.0;

    /*
     * Keep RA within [0,360).
     */
    ra_deg = normalize_degrees(ra_deg);

    /*
     * Recalculate radians after precession.
     */
    ra_rad = ra_deg * DEG_TO_RAD;
    dec_rad = dec_deg * DEG_TO_RAD;

    /*
     * ------------------------------------------------------------
     * 3. Convert local civil time -> UTC
     * ------------------------------------------------------------
     */
    double hour_utc =
        (double)hour
        + (double)minute / 60.0
        + (double)second / 3600.0
        - utc_offset;

    /*
     * ------------------------------------------------------------
     * 4. Greenwich Mean Sidereal Time
     * ------------------------------------------------------------
     */
    double gmst = gmst_simple(
        year,
        month,
        day,
        hour_utc
    );

    /*
     * ------------------------------------------------------------
     * 5. Local Hour Angle
     * ------------------------------------------------------------
     *
     * H = GMST + longitude - RA
     *
     * longitude is positive east.
     */
    double hour_angle_deg =
        gmst + longitude - ra_deg;

    hour_angle_deg = normalize_degrees(hour_angle_deg);

    double hour_angle = hour_angle_deg * DEG_TO_RAD;

    /*
     * ------------------------------------------------------------
     * 6. Observer latitude
     * ------------------------------------------------------------
     */
    double latitude_rad = latitude * DEG_TO_RAD;

    double sin_lat = sin(latitude_rad);
    double cos_lat = cos(latitude_rad);

    /*
     * ------------------------------------------------------------
     * 7. Altitude
     * ------------------------------------------------------------
     *
     * sin(h) =
     *     sin(dec) * sin(lat)
     *   + cos(dec) * cos(lat) * cos(H)
     */
    double sin_dec = sin(dec_rad);
    double cos_dec = cos(dec_rad);

    double cos_H = cos(hour_angle);

    double sin_alt =
        sin_dec * sin_lat
        + cos_dec * cos_lat * cos_H;

    /*
     * Protect against floating-point rounding.
     */
    if (sin_alt > 1.0) {
        sin_alt = 1.0;
    } else if (sin_alt < -1.0) {
        sin_alt = -1.0;
    }

    double altitude = asin(sin_alt);

    /*
     * ------------------------------------------------------------
     * 8. Azimuth
     * ------------------------------------------------------------
     *
     * atan2() is preferable to acos():
     *
     *   az = atan2(
     *       -sin(H),
     *       tan(dec)*cos(lat)
     *           - sin(lat)*cos(H)
     *   )
     *
     * This directly gives the correct quadrant.
     */
    double azimuth =
        atan2(
            -sin(hour_angle),
            tan(dec_rad) * cos_lat
                - sin_lat * cos_H
        );

    /*
     * Convert radians -> degrees and normalize to [0,360).
     */
    double altitude_deg = altitude * RAD_TO_DEG;

    double azimuth_deg =
        normalize_degrees(azimuth * RAD_TO_DEG);

    /*
     * ------------------------------------------------------------
     * 9. Return tuple
     * ------------------------------------------------------------
     */
    mp_obj_t result[3] = {
        mp_obj_new_float(gmst),
        mp_obj_new_float(altitude_deg),
        mp_obj_new_float(azimuth_deg),
    };

    return mp_obj_new_tuple(3, result);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(altaz_calculate_obj, 11, 11, altaz_calculate);

static const mp_rom_map_elem_t altaz_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_altaz) },
    { MP_ROM_QSTR(MP_QSTR_calculate), MP_ROM_PTR(&altaz_calculate_obj) },
};
static MP_DEFINE_CONST_DICT(altaz_module_globals, altaz_module_globals_table);

const mp_obj_module_t altaz_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&altaz_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_altaz, altaz_user_cmodule);