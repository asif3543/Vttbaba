import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import OWNER_ID, ALLOWED_USERS, STORAGE_CHANNEL_ID, BOT_USERNAME
from database import db
from datetime import datetime

router = Router()
multi_sel = {}

class States(StatesGroup):
    wait_post = State()
    wait_type = State()
    wait_single = State()
    wait_batch_ep = State()
    wait_batch_range = State()
    wait_short_url = State()
    wait_short_api = State()
    wait_prem_id = State()

def is_admin(uid):
    return uid == OWNER_ID or uid in ALLOWED_USERS

async def shortlink(shortner, url):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(shortner["url"], json={"api": shortner["api"], "url": url}, timeout=10) as r:
                if r.status == 200:
                    d = await r.json()
                    return d.get("short_url") or d.get("shortened_url") or url
    except: pass
    return url

@router.message(Command("start"))
async def start(m: Message):
    await m.reply("🤖 Bot alive!\n\n/post - Upload\n/add shortner account\n/remove shortner account\n/add premium\n/remove premium\n/show premium list\n/Force sub\n/send\n/send more channel\n/confirm\n/hmm\n/hu hu\n/delete")

@router.message(Command("post"))
async def post_cmd(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.reply("📤 Send post")
    await state.set_state(States.wait_post)

@router.message(States.wait_post)
async def got_post(m: Message, state: FSMContext):
    if m.forward_from_chat or m.forward_from:
        s = await m.bot.forward_message(STORAGE_CHANNEL_ID, m.chat.id, m.message_id)
        await db.save_temp(m.from_user.id, {"sid": s.message_id})
        await m.reply("✅ Post received. single link or batch link?")
        await state.set_state(States.wait_type)
    else:
        await m.reply("❌ Forward a post")

@router.message(States.wait_type)
async def link_type(m: Message, state: FSMContext):
    t = await db.get_temp(m.from_user.id)
    if "batch" in m.text.lower():
        await db.save_temp(m.from_user.id, {**t, "type": "batch", "eps": []})
        await m.reply("📚 Send episode (forward) or type 'done'")
        await state.set_state(States.wait_batch_ep)
    else:
        await db.save_temp(m.from_user.id, {**t, "type": "single"})
        await m.reply("🎬 Send episode")
        await state.set_state(States.wait_single)

@router.message(States.wait_single)
async def single_ep(m: Message, state: FSMContext):
    ep = m.text.strip()
    t = await db.get_temp(m.from_user.id)
    await db.save_temp(m.from_user.id, {**t, "episode": ep})
    await m.reply(f"✅ Episode {ep}\n/confirm")
    await state.clear()

@router.message(States.wait_batch_ep)
async def batch_ep(m: Message, state: FSMContext):
    t = await db.get_temp(m.from_user.id)
    eps = t.get("eps", [])
    if m.forward_from_chat or m.forward_from:
        eps.append(m.message_id)
        await db.save_temp(m.from_user.id, {**t, "eps": eps})
        await m.reply(f"✅ {len(eps)} received. Send next or 'done'")
    elif m.text and m.text.lower() == "done":
        if len(eps) < 2:
            await m.reply("❌ Need 2+ episodes")
            return
        await m.reply("✅ Enter range (05-15)")
        await state.set_state(States.wait_batch_range)
    else:
        await m.reply("❌ Forward an episode")

@router.message(States.wait_batch_range)
async def batch_range(m: Message, state: FSMContext):
    rng = m.text.strip()
    t = await db.get_temp(m.from_user.id)
    await db.save_temp(m.from_user.id, {**t, "batch_range": rng})
    await m.reply(f"✅ Range {rng}\n/confirm")
    await state.clear()

@router.message(Command("confirm"))
@router.message(Command("hmm"))
async def confirm_post(m: Message, state: FSMContext):
    t = await db.get_temp(m.from_user.id)
    if not t: return await m.reply("❌ No pending post")
    sn = await db.get_random_shortner()
    if t.get("type") == "batch":
        val = t.get("batch_range","1")
        btn = f"🎬 Watch {val}"
    else:
        val = t.get("episode","1")
        btn = f"🎬 Watch {val}"
    url = f"https://t.me/{BOT_USERNAME}?start=ep_{val}"
    if sn: url = await shortlink(sn, url)
    button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn, url=url)]])
    await m.bot.copy_message(m.chat.id, STORAGE_CHANNEL_ID, t["sid"], reply_markup=button)
    await db.save_post({"sid": t["sid"], "type": t.get("type"), "episode": t.get("episode"), "batch_range": t.get("batch_range"), "url": url})
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Send", callback_data="send_single")],[InlineKeyboardButton(text="📤 Send more", callback_data="send_multi")]])
    await m.reply("[ Send ]\n[ Send more ]", reply_markup=kb)
    await db.del_temp(m.from_user.id)

@router.callback_query(F.data == "send_single")
async def send_single_cb(cb: CallbackQuery):
    chs = await db.get_channels()
    if not chs: return await cb.message.reply("❌ No channels")
    kb = []
    for ch in chs:
        kb.append([InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")])
    await cb.message.reply("Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("single_"))
async def single_ch(cb: CallbackQuery):
    cid = int(cb.data.split("_")[1])
    await db.save_temp(cb.from_user.id, {"send_cid": cid, "send_type": "single"})
    await cb.message.reply("confirm please")

@router.callback_query(F.data == "send_multi")
async def send_multi_cb(cb: CallbackQuery):
    chs = await db.get_channels()
    if not chs: return await cb.message.reply("❌ No channels")
    kb = []
    for ch in chs:
        kb.append([InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    kb.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await cb.message.reply("Select channels (tap, then Done):", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("multi_") & ~F.data == "multi_done")
async def multi_tap(cb: CallbackQuery):
    cid = cb.data.split("_")[1]
    uid = cb.from_user.id
    if uid not in multi_sel: multi_sel[uid] = []
    if cid in multi_sel[uid]:
        multi_sel[uid].remove(cid)
        await cb.answer("Removed")
    else:
        multi_sel[uid].append(cid)
        await cb.answer("Added")
    chs = await db.get_channels()
    kb = []
    for ch in chs:
        c = "✅" if str(ch["_id"]) in multi_sel[uid] else "☐"
        kb.append([InlineKeyboardButton(text=f"{c} {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    kb.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "multi_done")
async def multi_done(cb: CallbackQuery):
    uid = cb.from_user.id
    sel = multi_sel.get(uid, [])
    if not sel: return await cb.message.reply("❌ None selected")
    await db.save_temp(uid, {"send_cids": sel, "send_type": "multi"})
    await cb.message.reply(f"✅ {len(sel)} selected\nconfirm please")

@router.message(Command("confirm"))
async def confirm_send(m: Message):
    t = await db.get_temp(m.from_user.id)
    post = await db.get_latest_post()
    if not post: return await m.reply("❌ No post")
    if t.get("send_type") == "single" and t.get("send_cid"):
        try:
            await m.bot.copy_message(t["send_cid"], STORAGE_CHANNEL_ID, post["sid"])
            await m.reply("✅ Sent")
        except Exception as e: await m.reply(f"❌ {e}")
    elif t.get("send_type") == "multi" and t.get("send_cids"):
        ok = 0
        for cid in t["send_cids"]:
            try:
                await m.bot.copy_message(int(cid), STORAGE_CHANNEL_ID, post["sid"])
                ok+=1
            except: pass
        await m.reply(f"✅ Sent to {ok} channels")
    await db.del_temp(m.from_user.id)
    if m.from_user.id in multi_sel: del multi_sel[m.from_user.id]

@router.message(Command("send"))
async def send_cmd(m: Message):
    if not is_admin(m.from_user.id): return
    chs = await db.get_channels()
    if not chs: return await m.reply("❌ No channels")
    kb = []
    for ch in chs:
        kb.append([InlineKeyboardButton(text=ch["name"], callback_data=f"single_{ch['_id']}")])
    await m.reply("Select channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(Command("send more channel"))
async def send_more_cmd(m: Message):
    if not is_admin(m.from_user.id): return
    chs = await db.get_channels()
    if not chs: return await m.reply("❌ No channels")
    kb = []
    for ch in chs:
        kb.append([InlineKeyboardButton(text=f"☐ {ch['name']}", callback_data=f"multi_{ch['_id']}")])
    kb.append([InlineKeyboardButton(text="✅ Done", callback_data="multi_done")])
    await m.reply("Select channels:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# Shortner
@router.message(Command("add shortner account"))
async def add_short(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.reply("🔗 Deskboard URL")
    await state.set_state(States.wait_short_url)
@router.message(States.wait_short_url)
async def short_url(m: Message, state: FSMContext):
    await state.update_data(url=m.text)
    await m.reply("🔑 API Token")
    await state.set_state(States.wait_short_api)
@router.message(States.wait_short_api)
async def short_api(m: Message, state: FSMContext):
    d = await state.get_data()
    await db.add_shortner(d["url"], m.text)
    await m.reply("✅ Added")
    await state.clear()

@router.message(Command("remove shortner account"))
async def rm_short(m: Message):
    if not is_admin(m.from_user.id): return
    ss = await db.get_shortners()
    if not ss: return await m.reply("❌ No shortners")
    kb = []
    for s in ss:
        kb.append([InlineKeyboardButton(text=s["url"], callback_data=f"del_{s['_id']}")])
    await m.reply("Select:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("del_"))
async def del_short(cb: CallbackQuery, state: FSMContext):
    sid = cb.data.split("_")[1]
    await state.update_data(sid=sid)
    await cb.message.reply("Type /delete to confirm")
@router.message(Command("delete"))
async def delete_short(m: Message, state: FSMContext):
    d = await state.get_data()
    if d.get("sid"):
        await db.remove_shortner(d["sid"])
        await m.reply("✅ Deleted")
        await state.clear()
    else: await m.reply("❌ No shortner selected")

# Premium
@router.message(Command("add premium"))
async def add_prem(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.reply("Send user ID")
    await state.set_state(States.wait_prem_id)
@router.message(States.wait_prem_id)
async def prem_id(m: Message, state: FSMContext):
    uid = int(m.text.strip())
    exp = await db.add_premium(uid)
    await m.reply(f"✅ Premium added to {uid}\nValid until {exp.strftime('%Y-%m-%d')}\n/hu hu to confirm")
    await state.update_data(prem_uid=uid)
@router.message(Command("hu hu"))
async def confirm_prem(m: Message, state: FSMContext):
    d = await state.get_data()
    if d.get("prem_uid"):
        await m.reply(f"✅ Confirmed premium for {d['prem_uid']} 🪄")
        await state.clear()
    else: await m.reply("❌ No pending")

@router.message(Command("remove premium"))
async def rm_prem(m: Message):
    if not is_admin(m.from_user.id): return
    try:
        uid = int(m.text.split()[1])
        await db.remove_premium(uid)
        await m.reply(f"✅ Removed and banned {uid}")
    except: await m.reply("❌ Usage: /remove premium user_id")

@router.message(Command("show premium list"))
async def show_prem(m: Message):
    if not is_admin(m.from_user.id): return
    users = await db.get_premium_list()
    if not users: return await m.reply("📭 No premium users")
    txt = "🌟 Premium Users:\n"
    for u in users:
        txt += f"• {u['_id']} - expires {u['expiry'].strftime('%Y-%m-%d')}\n"
    await m.reply(txt)

# Force Sub
@router.message(Command("Force sub"))
async def force_sub(m: Message):
    if not is_admin(m.from_user.id): return
    await m.reply("Forward a message from the channel")
    @router.message()
    async def fwd(msg: Message):
        if msg.forward_from_chat:
            cid = msg.forward_from_chat.id
            name = msg.forward_from_chat.title or str(cid)
            link = f"https://t.me/{name}"
            await db.add_fsub(cid, name, link)
            await msg.reply(f"✅ Added {name}")
        else: await msg.reply("❌ Forward a channel message")

@router.message(Command("send"))
async def send_cmd(m: Message): pass  # already above

@router.message(Command("send more channel"))
async def send_more_cmd(m: Message): pass

@router.message(Command("start"))
async def start_ep(m: Message):
    if " ep_" in m.text:
        ep = m.text.split("ep_")[1].strip()
        uid = m.from_user.id
        if await db.is_banned(uid): return await m.reply("❌ Banned")
        if await db.is_premium(uid):
            post = await db.get_post_by_episode(ep)
            if post: await m.bot.copy_message(uid, STORAGE_CHANNEL_ID, post["sid"])
            else: await m.reply("❌ Not found")
            return
        fsub = await db.get_fsub()
        for ch in fsub:
            try:
                mem = await m.bot.get_chat_member(ch["_id"], uid)
                if mem.status not in ["member","administrator","creator"]:
                    kb = []
                    for c in fsub: kb.append([InlineKeyboardButton(text=f"Join {c['name']}", url=c["link"])])
                    kb.append([InlineKeyboardButton(text="✅ Try Again", callback_data=f"retry_{ep}")])
                    await m.reply("❌ Join first", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                    return
            except: pass
        sn = await db.get_random_shortner()
        url = f"https://t.me/{BOT_USERNAME}?start=ep_{ep}"
        if sn: url = await shortlink(sn, url)
        await m.reply(f"🔗 Solve shortner:\n{url}\nAfter solving, you'll get episode.")

@router.callback_query(F.data.startswith("retry_"))
async def retry(cb: CallbackQuery):
    ep = cb.data.split("_")[1]
    await cb.message.delete()
    await start_ep(cb.message)
