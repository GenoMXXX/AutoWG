# wg-watchdog

## Назначение

`wg-watchdog` - локальный `opkg`-пакет для Keenetic с Entware. Он следит за
выбранным WireGuard-интерфейсом прямо на роутере и перезапускает его, если
входящий трафик не идет, а исходящий уже есть.

Проект полностью локальный:

- не использует Keenetic HTTP API;
- не требует логина и пароля;
- читает статистику из `/sys/class/net`;
- поднимает простой веб-интерфейс через `busybox httpd`.
- запускается как сервис и сам поднимает упавшие процессы обратно;
- умеет подождать после boot, чтобы роутер успел поднять сеть.

## Как работает

Пакет проверяет интерфейс и делает `down -> up`, если выполняются оба условия:

- `rxbytes == 0`
- `txbytes > TX_THRESHOLD`

По умолчанию:

- `RX_THRESHOLD=0`
- `TX_THRESHOLD=1024`

Сервисный слой:

- `BOOT_DELAY` - пауза перед стартом после загрузки роутера;
- `RESTART_DELAY` - пауза перед повторным запуском упавшего процесса.

## Установка

### Entware / Keenetic

Добавьте feed в `/opt/etc/opkg.conf`:

```sh
src/gz AutoWG https://GenoMXXX.github.io/AutoWG/opkg
```

Затем:

```sh
opkg update
opkg install wg-watchdog
/opt/etc/init.d/S99wg-watchdog start
```

Веб-панель:

```text
http://<IP роутера>:18088
```

## Сборка

Собрать пакет локально:

```sh
python build_ipk.py
```

Итоговый файл:

```text
wg-watchdog_1.0.0_all.ipk
```

## Что внутри

- `CONTROL/` - метаданные `opkg`
- `opt/bin/wg-watchdogd` - daemon
- `opt/etc/init.d/S99wg-watchdog` - автозапуск
- `opt/share/wg-watchdog/www` - веб-интерфейс и CGI

## Поддержка

Если нужно, можно следующим шагом добавить:

- сборку релизов через GitHub Actions;
- автопубликацию `.ipk` в Releases;
- страницу с короткой установкой в стиле публичного проекта.
