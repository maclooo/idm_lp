from vkbottle.api import UserApi
from vkbottle.rule import FromMe
from vkbottle.user import Blueprint, Message

from logger import logger_decorator
from objects import Database, IgnoredMembers
from utils import edit_message, get_ids_by_message, get_full_name_by_member_id

user = Blueprint(
    name='ignored_members_blueprint'
)


def add_ignore_member(database: Database, member_id: int, peer_id: int) -> None:
    database.ignored_members.append(
        IgnoredMembers(
            member_id=member_id,
            chat_id=peer_id
        )
    )
    database.save()


def remove_ignore_member(database: Database, member_id: int, peer_id: int) -> None:
    ignored_member = None
    for ign in database.ignored_members:
        if ign.member_id == member_id and ign.chat_id == peer_id:
            ignored_member = ign
    database.ignored_members.remove(ignored_member)
    database.save()


async def show_ignore_members(
        database: Database,
        api: UserApi,
        peer_id: int
) -> str:
    user_ids = [
        ignore_member.member_id
        for ignore_member in database.ignored_members
        if ignore_member.chat_id == peer_id and ignore_member.member_id > 0
    ]
    group_ids = [
        abs(ignore_member.member_id)
        for ignore_member in database.ignored_members
        if ignore_member.chat_id == peer_id and ignore_member.member_id < 0
    ]

    if not user_ids and not group_ids:
        return "📃 Ваш игнор-лист пуст"

    index = 1
    message = "📃 Ваш игнор-лист для этого чата\n"

    if user_ids:
        for vk_user in await api.users.get(user_ids=user_ids):
            message += f"{index}. [id{vk_user.id}|{vk_user.first_name} {vk_user.last_name}]\n"
            index += 1

    if group_ids:
        for vk_group in await api.groups.get_by_id(group_ids=group_ids):
            message += f'{index}. [club{vk_group.id}|{vk_group.name}]'
            index += 1
    return message


@user.on.message_handler(
    FromMe(),
    text=[
        '<prefix:service_prefix> +игнор [id<user_id:int>|<foo>',
        '<prefix:service_prefix> +игнор [club<group_id:int>|<foo>',
        '<prefix:service_prefix> +игнор https://vk.com/<domain>',
        '<prefix:service_prefix> +игнор',
    ]
)
@logger_decorator
async def add_ignored_member_wrapper(
        message: Message,
        domain: str = None,
        user_id: int = None,
        group_id: int = None,
        **kwargs
):
    db = Database.get_current()
    member_id = user_id if user_id else None
    if not user_id and group_id:
        member_id = -group_id

    member_ids = await get_ids_by_message(message, member_id, domain)
    if not member_ids:
        await edit_message(
            message,
            f'⚠ Необходимо указать пользователей'
        )
        return

    member_id = member_ids[0]
    if member_id == await message.api.user_id:
        await edit_message(
            message,
            f'⚠ Нельзя занести себя в игнор!'
        )
        return

    if member_id > 0:
        name = f'Пользователь  [id{member_id}|{await get_full_name_by_member_id(message.api, member_id)}]'
    else:
        name = f'Группа [club{abs(member_id)}|{await get_full_name_by_member_id(message.api, member_id)}]'

    if member_id in [
        igrored_member.member_id
        for igrored_member in db.ignored_members
        if igrored_member.chat_id == message.peer_id
    ]:
        await edit_message(
            message,
            f'⚠ {name} уже в списке игнорируемых'
        )
        return
    add_ignore_member(db, member_id, message.peer_id)
    await edit_message(
        message,
        f'✅ {name} добавлен в игнор-лист'
    )


@user.on.message_handler(
    FromMe(),
    text=[
        '<prefix:service_prefix> -игнор [id<user_id:int>|<foo>',
        '<prefix:service_prefix> -игнор [club<group_id:int>|<foo>',
        '<prefix:service_prefix> -игнор https://vk.com/<domain>',
        '<prefix:service_prefix> -игнор',
    ]
)
@logger_decorator
async def remove_ignored_member_wrapper(
        message: Message,
        domain: str = None,
        user_id: int = None,
        group_id: int = None,
        **kwargs
):
    db = Database.get_current()
    member_id = user_id if user_id else None
    if not user_id and group_id:
        member_id = -group_id

    member_ids = await get_ids_by_message(message, member_id, domain)
    if not member_ids:
        await edit_message(
            message,
            f'⚠ Необходимо указать пользователей'
        )
        return

    member_id = member_ids[0]

    if member_id > 0:
        name = f'Пользователь  [id{member_id}|{await get_full_name_by_member_id(message.api, member_id)}]'
    else:
        name = f'Группа [club{abs(member_id)}|{await get_full_name_by_member_id(message.api, member_id)}]'

    if member_id not in [
        igrored_member.member_id
        for igrored_member in db.ignored_members
        if igrored_member.chat_id == message.peer_id
    ]:
        await edit_message(
            message,
            f'⚠ {name} не в списке игнорируемых'
        )
        return
    remove_ignore_member(db, member_id, message.peer_id)
    await edit_message(
        message,
        f'✅ {name} удален из игнор-листа'
    )


@user.on.message_handler(
    FromMe(),
    text=[
        '<prefix:service_prefix> игнорлист',
        '<prefix:service_prefix> игнор лист',
    ]
)
@logger_decorator
async def show_ignore_members_wrapper(message: Message, **kwargs):
    db = Database.get_current()
    await edit_message(
        message,
        await show_ignore_members(
            db,
            message.api,
            message.peer_id
        )
    )
