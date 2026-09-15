from __future__ import annotations

LANGUAGES = {
    "en": "English",
    "ru": "Русский",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # first launch
        "fl.title": "Welcome to NIX",
        "fl.hint1": "First launch in this directory.",
        "fl.hint2": "NIX creates .nix/ for its state. Source files stay untouched.",
        "fl.choose_name": "Choose your pet's name:",
        "fl.name_placeholder": "pet name",
        "fl.create": "Create",
        "fl.language": "Language",
        "fl.empty_name": "Name cannot be empty",
        "welcome_back": "Welcome back, {name}!",

        # buttons
        "btn.scan": "Scan",
        "btn.status": "Status",
        "btn.pet": "Pet",
        "btn.settings": "Settings",
        "btn.help": "Help",
        "btn.clear": "Clear",
        "btn.quit": "Quit",

        # input
        "cmd.placeholder": "Type /command, e.g. /help ...",

        # session
        "session.started": "session started  root={root}",
        "session.foundation": "stage A foundation  ·  mutation engine disabled",
        "session.hint": "type /help or press buttons below",
        "pet.created": "pet created: {name}",
        "pet.no_pet": "no pet yet",

        # help/status/settings/logs/history
        "tbl.commands": "Commands",
        "tbl.command": "Command",
        "tbl.description": "Description",
        "tbl.project_status": "Project Status",
        "tbl.key": "Key",
        "tbl.value": "Value",
        "tbl.extensions": "Extensions",
        "tbl.extension": "Extension",
        "tbl.count": "Count",
        "tbl.scan": "Scan Summary",
        "tbl.pet": "Pet: {name}",
        "tbl.attribute": "Attribute",
        "tbl.settings": "Settings",
        "tbl.setting": "Setting",
        "tbl.session_log": "Session Log",
        "tbl.journal": "Journal",
        "tbl.time": "Time",
        "tbl.kind": "Kind",
        "tbl.message": "Message",
        "modal.close": "Close (Esc)",
        "set.saved": "Settings saved",

        # status rows
        "st.root": "Root",
        "st.mode": "Mode",
        "st.attempts": "Attempts",
        "st.files": "Files",
        "st.dirs": "Directories",
        "st.source": "Source",
        "st.functions": "Functions",
        "st.classes": "Classes",
        "st.lines": "Lines",

        # pet rows
        "pet.name": "Name",
        "pet.mood": "Mood",
        "pet.energy": "Energy",
        "pet.age": "Age",
        "pet.body": "Body",
        "pet.scans": "Scans",
        "pet.stage": "Stage",
        "pet.pattern.seed": "Seed",
        "pet.pattern.sprout": "Sprout",
        "pet.pattern.bloom": "Bloom",
        "pet.pattern.seed": "Seed",
        "pet.pattern.sprout": "Sprout",
        "pet.pattern.bloom": "Bloom",
        "pet.mutations": "Mutations",
        "pet.failures": "Failures",

        # settings rows
        "set.theme": "Theme",
        "set.attempts": "Attempts",
        "set.mutation_budget": "Mutation budget",
        "set.tamagotchi": "Tamagotchi",
        "set.animations": "Animations",
        "set.avatar": "Avatar",
        "set.sounds": "Sounds",
        "set.auto_scan": "Auto scan",
        "set.checkpoint": "Checkpoint on mutate",
        "set.git": "Git auto commit",
        "set.protected": "Protected",
        "on": "on",
        "off": "off",
        "set.language": "Language",

        # scan
        "scan.files": "files",
        "scan.dirs": "dirs",
        "scan.functions": "functions",
        "scan.classes": "classes",
        "scan.lines": "lines",
        "scan.no_ext": "no extensions found",

        # command descriptions
        "cmd.help.desc": "show this help",
        "cmd.status.desc": "current project and NIX state",
        "cmd.scan.desc": "read-only project inventory",
        "cmd.attempts.desc": "show/set attempt budget",
        "cmd.pet.desc": "show pet status",
        "cmd.mode.desc": "show safety mode",
        "cmd.settings.desc": "current settings",
        "cmd.logs.desc": "show session log",
        "cmd.history.desc": "show journal history",
        "cmd.clear.desc": "clear the event log",
        "cmd.quit.desc": "exit NIX",
        "cmd.version.desc": "show NIX version",
        "cmd.pwd.desc": "show current working directory",
        "cmd.mode.local": "local",
        "cmd.mode.safe": "safe",
        "cmd.mode.git": "git",
        "cmd.mode.valid": "valid modes: {modes}",

        # feedback
        "fb.attempts": "attempts: {cur}/{max}",
        "fb.attempts_set": "attempts: {cur}/{max}",
        "fb.attempts_invalid": "usage: /attempts N | /attempts +N | /attempts -N",
        "fb.mode": "mode: {mode}",
        "fb.mode_set": "mode set to: {mode}",
        "fb.unknown": "Unknown command: /{name}. Type /help.",
        "fb.not_command": "Commands must start with '/'. Type /help.",
        "fb.failed": "/{name} failed: {exc}",
        "fb.version": "NIX v{version}",
        "fb.no_logs": "no log entries yet",
        "fb.no_history": "no journal entries today",

        # moods
        "mood.curious": "curious",
        "mood.happy": "happy",
        "mood.content": "content",
        "mood.focused": "focused",
        "mood.alert": "alert",
        "mood.determined": "determined",
        "mood.thoughtful": "thoughtful",
        "mood.cautious": "cautious",
        "mood.worried": "worried",
        "mood.relieved": "relieved",
        "mood.tired": "tired",
        "mood.anxious": "anxious",
    },
    "ru": {
        # first launch
        "fl.title": "Добро пожаловать в NIX",
        "fl.hint1": "Первый запуск в этой папке.",
        "fl.hint2": "NIX создаст .nix/ для своего состояния. Исходники не тронуты.",
        "fl.choose_name": "Выбери имя питомца:",
        "fl.name_placeholder": "имя питомца",
        "fl.create": "Создать",
        "fl.language": "Язык",
        "fl.empty_name": "Имя не может быть пустым",
        "welcome_back": "С возвращением, {name}!",

        # buttons
        "btn.scan": "Скан",
        "btn.status": "Статус",
        "btn.pet": "Питомец",
        "btn.settings": "Настройки",
        "btn.help": "Помощь",
        "btn.clear": "Очистить",
        "btn.quit": "Выход",

        # input
        "cmd.placeholder": "Введите /команду, напр. /help ...",

        # session
        "session.started": "сессия начата  root={root}",
        "session.foundation": "фундамент этапа A · движок мутаций выключен",
        "session.hint": "наберите /help или нажмите кнопки ниже",
        "pet.created": "питомец создан: {name}",
        "pet.no_pet": "питомца ещё нет",

        # help/status/settings/logs/history
        "tbl.commands": "Команды",
        "tbl.command": "Команда",
        "tbl.description": "Описание",
        "tbl.project_status": "Статус проекта",
        "tbl.key": "Параметр",
        "tbl.value": "Значение",
        "tbl.extensions": "Расширения",
        "tbl.extension": "Расширение",
        "tbl.count": "Количество",
        "tbl.scan": "Сводка сканирования",
        "tbl.pet": "Питомец: {name}",
        "tbl.attribute": "Атрибут",
        "tbl.settings": "Настройки",
        "tbl.setting": "Настройка",
        "tbl.session_log": "Журнал сессии",
        "tbl.journal": "Журнал",
        "tbl.time": "Время",
        "tbl.kind": "Тип",
        "tbl.message": "Сообщение",
        "modal.close": "Закрыть (Esc)",
        "set.saved": "Настройки сохранены",

        # status rows
        "st.root": "Корень",
        "st.mode": "Режим",
        "st.attempts": "Попытки",
        "st.files": "Файлы",
        "st.dirs": "Папки",
        "st.source": "Исходники",
        "st.functions": "Функции",
        "st.classes": "Классы",
        "st.lines": "Строки",

        # pet rows
        "pet.name": "Имя",
        "pet.mood": "Настроение",
        "pet.energy": "Энергия",
        "pet.age": "Возраст",
        "pet.body": "Тело",
        "pet.scans": "Сканы",
        "pet.stage": "Стадия",
        "pet.pattern.seed": "Семечко",
        "pet.pattern.sprout": "Росток",
        "pet.pattern.bloom": "Цветение",
        "pet.mutations": "Мутации",
        "pet.failures": "Провалы",

        # settings rows
        "set.theme": "Тема",
        "set.attempts": "Попытки",
        "set.mutation_budget": "Бюджет мутаций",
        "set.tamagotchi": "Тамагочи",
        "set.animations": "Анимации",
        "set.avatar": "Аватар",
        "set.sounds": "Звуки",
        "set.auto_scan": "Авто-скан",
        "set.checkpoint": "Чекпоинт при мутации",
        "set.git": "Авто-коммит Git",
        "set.protected": "Защищённые",
        "on": "вкл",
        "off": "выкл",
        "set.language": "Язык",

        # scan
        "scan.files": "файлов",
        "scan.dirs": "папок",
        "scan.functions": "функций",
        "scan.classes": "классов",
        "scan.lines": "строк",
        "scan.no_ext": "расширений не найдено",

        # command descriptions
        "cmd.help.desc": "показать помощь",
        "cmd.status.desc": "текущий проект и состояние NIX",
        "cmd.scan.desc": "только чтение: инвентаризация проекта",
        "cmd.attempts.desc": "показать/установить бюджет попыток",
        "cmd.pet.desc": "состояние питомца",
        "cmd.mode.desc": "показать режим безопасности",
        "cmd.settings.desc": "текущие настройки",
        "cmd.logs.desc": "показать журнал сессии",
        "cmd.history.desc": "показать историю журнала",
        "cmd.clear.desc": "очистить лог событий",
        "cmd.quit.desc": "выйти из NIX",
        "cmd.version.desc": "показать версию NIX",
        "cmd.pwd.desc": "показать текущую папку",
        "cmd.mode.local": "local",
        "cmd.mode.safe": "safe",
        "cmd.mode.git": "git",
        "cmd.mode.valid": "допустимые режимы: {modes}",

        # feedback
        "fb.attempts": "попытки: {cur}/{max}",
        "fb.attempts_set": "попытки: {cur}/{max}",
        "fb.attempts_invalid": "использование: /attempts N | /attempts +N | /attempts -N",
        "fb.mode": "режим: {mode}",
        "fb.mode_set": "режим установлен: {mode}",
        "fb.unknown": "Неизвестная команда: /{name}. Наберите /help.",
        "fb.not_command": "Команды должны начинаться с '/'. Наберите /help.",
        "fb.failed": "/{name} не сработала: {exc}",
        "fb.version": "NIX v{version}",
        "fb.no_logs": "записей журнала ещё нет",
        "fb.no_history": "сегодня записей журнала нет",

        # moods
        "mood.curious": "любопытный",
        "mood.happy": "счастлив",
        "mood.content": "доволен",
        "mood.focused": "сосредоточен",
        "mood.alert": "насторожен",
        "mood.determined": "решителен",
        "mood.thoughtful": "задумчив",
        "mood.cautious": "осторожен",
        "mood.worried": "встревожен",
        "mood.relieved": "облегчён",
        "mood.tired": "устал",
        "mood.anxious": "взволнован",
    },
}

DEFAULT_LANGUAGE = "en"


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in TRANSLATIONS else DEFAULT_LANGUAGE
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text.replace("{", "").replace("}", "")
    return text