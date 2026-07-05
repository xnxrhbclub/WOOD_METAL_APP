[app]
title = Заказы
package.name = zakazy
package.domain = org.zakazy

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,db,ttf

version = 0.1

requirements = python3,kivy==2.3.0,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET

android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

icon.filename = icon.png

[buildozer]
log_level = 2
warn_on_root = 1
