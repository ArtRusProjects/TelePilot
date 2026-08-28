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

    double ra_deg = mp_obj_get_float(args[0]);
    double dec_deg = mp_obj_get_float(args[1]);
    int year = mp_obj_get_int(args[2]);
    int month = mp_obj_get_int(args[3]);
    int day = mp_obj_get_int(args[4]);
    double hour = mp_obj_get_int(args[5]);
    double minute = mp_obj_get_int(args[6]);
    double second = mp_obj_get_int(args[7]);
    double latitude = mp_obj_get_float(args[8]);
    double longitude = mp_obj_get_float(args[9]);
    double utc_offset = mp_obj_get_float(args[10]);

    double years = years_since_j2000(year, month, day);
    double m = 3.07496 + 0.00186 * years;
    double n = 1.33621 - 0.00057 * years;
    double ra_rad = ra_deg * DEG_TO_RAD;
    double dec_rad = dec_deg * DEG_TO_RAD;
    ra_deg += (m + n * sin(ra_rad) * tan(dec_rad)) / 3600.0;
    dec_deg += (n * cos(ra_rad)) / 3600.0;
    ra_rad = ra_deg * DEG_TO_RAD;
    dec_rad = dec_deg * DEG_TO_RAD;

    double hour_utc = hour + minute / 60.0 + second / 3600.0 - utc_offset;
    double gmst = gmst_simple(year, month, day, hour_utc);
    double hour_angle = normalize_degrees(gmst + longitude - ra_deg) * DEG_TO_RAD;
    double latitude_rad = latitude * DEG_TO_RAD;

    double sin_alt =
        sin(dec_rad) * sin(latitude_rad)
        + cos(dec_rad) * cos(latitude_rad) * cos(hour_angle);
    if (sin_alt > 1.0) {
        sin_alt = 1.0;
    } else if (sin_alt < -1.0) {
        sin_alt = -1.0;
    }
    double altitude = asin(sin_alt);
    double cos_az =
        (sin(dec_rad) - sin(altitude) * sin(latitude_rad))
        / (cos(altitude) * cos(latitude_rad));
    if (cos_az > 1.0) {
        cos_az = 1.0;
    } else if (cos_az < -1.0) {
        cos_az = -1.0;
    }
    double azimuth = acos(cos_az);
    if (sin(hour_angle) > 0.0) {
        azimuth = 2.0 * 3.14159265358979323846 - azimuth;
    }

    mp_obj_t result[3] = {
        mp_obj_new_float(gmst),
        mp_obj_new_float(altitude * RAD_TO_DEG),
        mp_obj_new_float(azimuth * RAD_TO_DEG),
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