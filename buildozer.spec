[app]
title = Заказы
package.name = zakazy
package.domain = org.zakazy

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,db
version = 0.1
icon.filename = %(source.dir)s/icon.png

requirements = python3,kivy==2.3.0,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED

# Минимальная и целевая версия Android API (можно оставить как есть для старта)
android.minapi = 21
android.api = 33
android.ndk = 25b

[buildozer]
log_level = 2
warn_on_root = 1
