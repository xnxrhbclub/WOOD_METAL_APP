[app]
title = Заказы
package.name = zakazy
package.domain = org.zakazy

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,db,ttf

version = 0.1

icon.filename = %(source.dir)s/icon.png

requirements = python3,kivy==2.3.0,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED

android.minapi = 21
android.api = 34
android.ndk = 25b
android.build_tools_version = 34.0.0

android.archs = arm64-v8a

[buildozer]

log_level = 2
warn_on_root = 1
