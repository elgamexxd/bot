import discord
from discord.ext import commands
from discord import app_commands
import json, os
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ╔══════════════════════════════════════════════════════════════╗
#  BURAYA DOLDUR ↓
# ╠══════════════════════════════════════════════════════════════╣

YETKİLİ_ROL_ID = 1485231204830810133

GREV_1_ROLE = 1484188685745524864
GREV_2_ROLE = 1484188685745524863
GREV_3_ROLE = 1484188685745524862
IHRAC_ROLE  = 1484188685745524865

RUTBE_ROLLERI = {
    "Cadet":           1484188685812629581,
    "Solo Cadet":      0,
    "Trooper I":       1484188685812629582,
    "Trooper II":      1484188685812629583,
    "Trooper III":     1484188685812629584,
    "Trooper III+I":   1484188685824950332,
    "Senior Trooper":  0,
    "Corporal":        1484188685824950333,
    "Sergeant I":      1484188685824950339,
    "Sergeant II":     1484188685824950340,
    "Senior Sergeant": 0,
    "Lieutenant I":    1484188685824950341,
    "Lieutenant II":   1484188685850120192,
    "Captain":         1484188685850120193,
    "High Command":    0,
    "Assistant Chief": 0,
    "Chief of Police": 0,
}

LOG_KANAL_ID   = 1485220707511046246
RAPOR_KANAL_ID = 1485225648510205972
IZIN_KANAL_ID  = 1485225720576872488
TERFI_KANAL_ID = 1485225786649870459

# ╚══════════════════════════════════════════════════════════════╝

DATA_FILE    = "sasp_data.json"
RUTBE_SIRASI = list(RUTBE_ROLLERI.keys())

SEBEP_SABLONLARI = [
    "FRP (Fail Roleplay)", "Görev İhmali", "Kural İhlali",
    "Yetkiyi Kötüye Kullanma", "Disiplin Bozukluğu",
    "Saygısızlık / Hakaret", "İzinsiz Eylem", "Diğer (Açıklayınız)",
]

NOBET_BOLGELER = [
    "Merkez Karakol", "Havalimanı", "Liman Bölgesi",
    "Kuzey Bölgesi", "Güney Bölgesi", "Doğu Bölgesi",
    "Batı Bölgesi", "Otoyol Devriyesi", "Özel Görev",
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def yetkili_mi(member: discord.Member) -> bool:
    if YETKİLİ_ROL_ID == 0:
        return member.guild_permissions.manage_roles
    return any(r.id == YETKİLİ_ROL_ID for r in member.roles)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_md(data, member_id):
    k = str(member_id)
    if k not in data:
        data[k] = {}
    for key, val in {
        "grev": 0, "ihrac": False, "gecmis": [], "not_listesi": [],
        "rutbe": None, "sicil": None, "giris_tarihi": None, "aktif": True,
        "izin_gecmisi": [], "aktif_izin": None,
        "nobet_gecmisi": [], "aktif_nobet": None,
        "terfi_gecmisi": [], "rapor_sayisi": 0,
    }.items():
        if key not in data[k]:
            data[k][key] = val
    return data[k]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def gecmis_kaydet(md, islem, sebep, yapan):
    md["gecmis"].append({"tarih": now_iso(), "islem": islem, "sebep": sebep, "yapan": yapan})

async def strike_rolleri_temizle(member):
    ids = {GREV_1_ROLE, GREV_2_ROLE, GREV_3_ROLE, IHRAC_ROLE}
    remove = [r for r in member.roles if r.id in ids]
    if remove:
        await member.remove_roles(*remove, reason="SASP strike güncelleme")

async def rutbe_rol_guncelle(member, eski_rutbe, yeni_rutbe):
    tum_ids = {rid for rid in RUTBE_ROLLERI.values() if rid != 0}
    kaldir = [r for r in member.roles if r.id in tum_ids]
    if kaldir:
        await member.remove_roles(*kaldir, reason="SASP rütbe güncelleme")
    if yeni_rutbe and RUTBE_ROLLERI.get(yeni_rutbe, 0) != 0:
        rol = member.guild.get_role(RUTBE_ROLLERI[yeni_rutbe])
        if rol:
            await member.add_roles(rol, reason=f"SASP: {yeni_rutbe}")

async def log_gonder(guild, embed):
    ch = guild.get_channel(LOG_KANAL_ID)
    if ch:
        try: await ch.send(embed=embed)
        except: pass

async def kanal_gonder(guild, kanal_id, embed, view=None):
    if not kanal_id: return None
    ch = guild.get_channel(kanal_id)
    if ch:
        try: return await ch.send(embed=embed, view=view) if view else await ch.send(embed=embed)
        except: pass
    return None

async def dm_bildirim(member, islem, sebep, yapan):
    try:
        e = discord.Embed(title="📢 SASP — Hesabınızda Güncelleme",
                          color=discord.Color.orange(), timestamp=datetime.now(timezone.utc))
        e.add_field(name="İşlem", value=islem, inline=True)
        e.add_field(name="Sebep", value=sebep,  inline=True)
        e.add_field(name="Yapan", value=yapan,  inline=False)
        e.set_footer(text="SASP Yönetim Sistemi")
        await member.send(embed=e)
    except discord.Forbidden:
        pass

async def log_isle(guild, hedef, islem, sebep, yapan_mention, renk=None):
    e = discord.Embed(title="📝 SASP Log", color=renk or discord.Color.orange(),
                      timestamp=datetime.now(timezone.utc))
    e.add_field(name="👤 Hedef", value=hedef.mention,  inline=True)
    e.add_field(name="🔨 İşlem", value=islem,           inline=True)
    e.add_field(name="📋 Sebep", value=sebep,            inline=False)
    e.add_field(name="👮 Yapan", value=yapan_mention,    inline=True)
    e.set_footer(text="SASP Yönetim Sistemi | with by elgamex")
    await log_gonder(guild, e)

def durum_embed(member, md):
    grev = md["grev"]; ihrac = md["ihrac"]; aktif = md.get("aktif", True)
    if ihrac:        renk = discord.Color.dark_red();  ds = "🔴 **İHRAÇ EDİLDİ**"
    elif not aktif:  renk = discord.Color.dark_gray(); ds = "⛔ Görevden Uzaklaştırıldı"
    elif grev == 3:  renk = discord.Color.red();       ds = "🚨 Strike 3/3"
    elif grev == 2:  renk = discord.Color.orange();    ds = "⚠️ Strike 2/3"
    elif grev == 1:  renk = discord.Color.yellow();    ds = "⚠️ Strike 1/3"
    else:            renk = discord.Color.green();     ds = "✅ Temiz"
    bar = "".join(["🟥" if i <= grev else "⬜" for i in range(1, 4)])
    e = discord.Embed(title="📋 SASP — Üye Profili", color=renk)
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="👤 Üye",   value=member.mention, inline=True)
    e.add_field(name="📊 Durum", value=ds,              inline=True)
    e.add_field(name="\u200b",   value="\u200b",         inline=True)
    if md.get("sicil"):        e.add_field(name="🪪 Sicil", value=f"`{md['sicil']}`",             inline=True)
    if md.get("rutbe"):        e.add_field(name="🎖️ Rütbe", value=md["rutbe"],                    inline=True)
    if md.get("giris_tarihi"): e.add_field(name="📅 Giriş", value=f"`{md['giris_tarihi'][:10]}`", inline=True)
    e.add_field(name="Strike Sayacı", value=f"{bar}  `{grev}/3`", inline=False)
    if md.get("aktif_izin"):
        iz = md["aktif_izin"]
        e.add_field(name="🏖️ Aktif İzin", value=f"{iz['baslangic']} → {iz['bitis']}\n_{iz['sebep']}_", inline=False)
    if md.get("aktif_nobet"):
        nb = md["aktif_nobet"]
        e.add_field(name="🚔 Aktif Nöbet", value=f"📍 {nb['bolge']} | {nb['baslangic'][:16].replace('T',' ')}", inline=False)
    if md.get("not_listesi"):
        e.add_field(name=f"📝 Notlar ({len(md['not_listesi'])})",
                    value="\n".join(f"• {n['icerik'][:60]}" for n in md["not_listesi"][-3:]), inline=False)
    son = md["gecmis"][-1] if md["gecmis"] else None
    if son:
        e.add_field(name="Son İşlem",
                    value=f"`{son['tarih'][:10]}` **{son['islem']}**\n📋 {son['sebep']}\n👤 {son['yapan']}",
                    inline=False)
    e.set_footer(text="SASP Yönetim Sistemi | with by elgamex")
    return e

def ana_menu_embed():
    e = discord.Embed(
        title="🚔 SASP — Ana Menü",
        description=(
            "**👮 Yönetim** → Strike, ihraç, profil işlemleri\n"
            "**🚔 Nöbet** → Nöbet başlat/bitir, aktif nöbetler\n"
            "**🎖️ Terfi** → Terfi yükselt/düşür, geçmiş\n"
            "**🏖️ İzin** → İzin talebi oluştur, izin yönetimi\n"
            "**🚨 Rapor** → Şikayet / rapor oluştur\n"
            "**📊 İstatistik** → Sunucu istatistikleri"
        ),
        color=discord.Color.blurple()
    )
    e.set_footer(text="SASP Yönetim Sistemi | with by elgamex")
    return e

# ══════════════════════════════════════════
#  MODALLAR
# ══════════════════════════════════════════
class SebepModal(discord.ui.Modal, title="İşlem Sebebi"):
    sebep_input = discord.ui.TextInput(label="Sebep", placeholder="Detaylı sebep yazın...",
                                       style=discord.TextStyle.paragraph, max_length=300)
    def __init__(self, cb):
        super().__init__(); self._cb = cb
    async def on_submit(self, interaction):
        await self._cb(interaction, str(self.sebep_input))

class NotModal(discord.ui.Modal, title="Not Ekle"):
    not_input = discord.ui.TextInput(label="Not", placeholder="Üye hakkında not yazın...",
                                     style=discord.TextStyle.paragraph, max_length=400)
    def __init__(self, hedef, yapan):
        super().__init__(); self.hedef = hedef; self.yapan = yapan
    async def on_submit(self, interaction):
        data = load_data(); md = get_md(data, self.hedef.id)
        md["not_listesi"].append({"tarih": now_iso(), "icerik": str(self.not_input), "yapan": str(interaction.user)})
        gecmis_kaydet(md, "Not Eklendi", str(self.not_input)[:60], str(interaction.user))
        save_data(data)
        await log_isle(interaction.guild, self.hedef, "Not Eklendi", str(self.not_input)[:80],
                       interaction.user.mention, discord.Color.blurple())
        await interaction.response.edit_message(embed=durum_embed(self.hedef, md),
                                                 view=StrikePaneli(self.hedef, self.yapan))

class ProfilModal(discord.ui.Modal, title="Profil Güncelle"):
    sicil = discord.ui.TextInput(label="Sicil No",     placeholder="Ör: SASP-0042",     required=False, max_length=20)
    rutbe = discord.ui.TextInput(label="Rütbe",        placeholder="Ör: Senior Trooper", required=False, max_length=40)
    giris = discord.ui.TextInput(label="Giriş Tarihi", placeholder="YYYY-MM-DD",         required=False, max_length=10)
    def __init__(self, hedef, yapan):
        super().__init__(); self.hedef = hedef; self.yapan = yapan
    async def on_submit(self, interaction):
        data = load_data(); md = get_md(data, self.hedef.id)
        if str(self.sicil): md["sicil"]        = str(self.sicil)
        if str(self.rutbe): md["rutbe"]        = str(self.rutbe)
        if str(self.giris): md["giris_tarihi"] = str(self.giris)
        gecmis_kaydet(md, "Profil Güncellendi", "Sicil/Rütbe/Giriş güncellendi", str(interaction.user))
        save_data(data)
        await interaction.response.edit_message(embed=durum_embed(self.hedef, md),
                                                 view=StrikePaneli(self.hedef, self.yapan))

class IzinTalebiModal(discord.ui.Modal, title="İzin Talebi"):
    baslangic = discord.ui.TextInput(label="Başlangıç Tarihi", placeholder="YYYY-MM-DD", max_length=10)
    bitis     = discord.ui.TextInput(label="Bitiş Tarihi",     placeholder="YYYY-MM-DD", max_length=10)
    sebep     = discord.ui.TextInput(label="İzin Sebebi",      placeholder="İzin sebebinizi yazın...",
                                     style=discord.TextStyle.paragraph, max_length=300)
    def __init__(self, talepci):
        super().__init__(); self.talepci = talepci
    async def on_submit(self, interaction):
        talep = {"id": f"{self.talepci.id}_{int(datetime.now(timezone.utc).timestamp())}",
                 "talepci_id": self.talepci.id, "baslangic": str(self.baslangic),
                 "bitis": str(self.bitis), "sebep": str(self.sebep), "tarih": now_iso(), "durum": "bekliyor"}
        e = discord.Embed(title="🏖️ İzin Talebi", color=discord.Color.yellow(), timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=self.talepci.display_avatar.url)
        e.add_field(name="👤 Talep Eden", value=self.talepci.mention, inline=True)
        e.add_field(name="📅 Başlangıç",  value=str(self.baslangic),  inline=True)
        e.add_field(name="📅 Bitiş",      value=str(self.bitis),      inline=True)
        e.add_field(name="📋 Sebep",      value=str(self.sebep),      inline=False)
        e.set_footer(text="SASP İzin Sistemi | with by elgamex")
        data = load_data()
        if "bekleyen_izinler" not in data: data["bekleyen_izinler"] = []
        data["bekleyen_izinler"].append(talep); save_data(data)
        await kanal_gonder(interaction.guild, IZIN_KANAL_ID, e, IzinOnayView(talep, self.talepci))
        await interaction.response.edit_message(embed=ana_menu_embed(), view=AnaMenuView(interaction.user))

class RaporModal(discord.ui.Modal, title="Şikayet / Rapor"):
    sikayet_edilen = discord.ui.TextInput(label="Şikayet Edilen", placeholder="Üye adı veya ID", max_length=50)
    konu           = discord.ui.TextInput(label="Konu",           placeholder="Kısa başlık",    max_length=100)
    aciklama       = discord.ui.TextInput(label="Açıklama",       placeholder="Detaylı anlat...",
                                          style=discord.TextStyle.paragraph, max_length=1000)
    kanitlar       = discord.ui.TextInput(label="Kanıt (link)",   placeholder="Ekran görüntüsü linki",
                                          required=False, max_length=300)
    def __init__(self, sikayet_eden):
        super().__init__(); self.sikayet_eden = sikayet_eden
    async def on_submit(self, interaction):
        e = discord.Embed(title="🚨 Yeni Şikayet / Rapor", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=self.sikayet_eden.display_avatar.url)
        e.add_field(name="📌 Şikayet Eden",   value=self.sikayet_eden.mention, inline=True)
        e.add_field(name="🎯 Şikayet Edilen", value=str(self.sikayet_edilen),  inline=True)
        e.add_field(name="📋 Konu",           value=str(self.konu),             inline=False)
        e.add_field(name="📝 Açıklama",       value=str(self.aciklama),         inline=False)
        if str(self.kanitlar): e.add_field(name="🔗 Kanıtlar", value=str(self.kanitlar), inline=False)
        e.set_footer(text="SASP Rapor Sistemi | with by elgamex")
        data = load_data(); md = get_md(data, self.sikayet_eden.id)
        md["rapor_sayisi"] = md.get("rapor_sayisi", 0) + 1
        if "raporlar" not in data: data["raporlar"] = []
        data["raporlar"].append({"tarih": now_iso(), "sikayet_eden": str(self.sikayet_eden),
                                  "sikayet_edilen": str(self.sikayet_edilen), "konu": str(self.konu),
                                  "aciklama": str(self.aciklama), "durum": "inceleniyor"})
        save_data(data)
        await kanal_gonder(interaction.guild, RAPOR_KANAL_ID, e)
        await interaction.response.edit_message(embed=ana_menu_embed(), view=AnaMenuView(interaction.user))

# ══════════════════════════════════════════
#  İZİN ONAY VIEW
# ══════════════════════════════════════════
class IzinOnayView(discord.ui.View):
    def __init__(self, talep, talepci):
        super().__init__(timeout=None); self.talep = talep; self.talepci = talepci

    @discord.ui.button(label="✅ Onayla", style=discord.ButtonStyle.success)
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
        await interaction.response.defer()
        data = load_data(); md = get_md(data, self.talepci.id)
        md["aktif_izin"] = {"baslangic": self.talep["baslangic"], "bitis": self.talep["bitis"],
                            "sebep": self.talep["sebep"], "onaylayan": str(interaction.user)}
        md["izin_gecmisi"].append({**md["aktif_izin"], "tarih": now_iso(), "durum": "onaylandi"})
        gecmis_kaydet(md, "İzin Onaylandı", f"{self.talep['baslangic']} → {self.talep['bitis']}", str(interaction.user))
        save_data(data)
        await dm_bildirim(self.talepci, "İzin Talebiniz Onaylandı ✅",
                          f"{self.talep['baslangic']} → {self.talep['bitis']}", str(interaction.user))
        emb = interaction.message.embeds[0]; emb.color = discord.Color.green()
        emb.title = "🏖️ İzin Talebi — ✅ ONAYLANDI"
        emb.add_field(name="👮 Onaylayan", value=interaction.user.mention, inline=True)
        for item in self.children: item.disabled = True
        await interaction.edit_original_response(embed=emb, view=self)

    @discord.ui.button(label="❌ Reddet", style=discord.ButtonStyle.danger)
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
        await interaction.response.defer()
        data = load_data(); md = get_md(data, self.talepci.id)
        md["izin_gecmisi"].append({"baslangic": self.talep["baslangic"], "bitis": self.talep["bitis"],
                                   "sebep": self.talep["sebep"], "tarih": now_iso(), "durum": "reddedildi",
                                   "reddeden": str(interaction.user)})
        gecmis_kaydet(md, "İzin Reddedildi", f"{self.talep['baslangic']} → {self.talep['bitis']}", str(interaction.user))
        save_data(data)
        await dm_bildirim(self.talepci, "İzin Talebiniz Reddedildi ❌",
                          f"{self.talep['baslangic']} → {self.talep['bitis']}", str(interaction.user))
        emb = interaction.message.embeds[0]; emb.color = discord.Color.red()
        emb.title = "🏖️ İzin Talebi — ❌ REDDEDİLDİ"
        emb.add_field(name="👮 Reddeden", value=interaction.user.mention, inline=True)
        for item in self.children: item.disabled = True
        await interaction.edit_original_response(embed=emb, view=self)

# ══════════════════════════════════════════
#  TERFİ OY VIEW
# ══════════════════════════════════════════
class TerfiOyView(discord.ui.View):
    def __init__(self, hedef_id, yeni_rutbe, eski_rutbe):
        super().__init__(timeout=86400)
        self.hedef_id = hedef_id; self.yeni_rutbe = yeni_rutbe
        self.eski_rutbe = eski_rutbe; self.oylar = {}

    def oy_bar(self):
        ev = sum(1 for v in self.oylar.values() if v)
        ha = sum(1 for v in self.oylar.values() if not v)
        return f"{'🟢'*min(ev,10)} **{ev}** Evet  |  **{ha}** Hayır {'🔴'*min(ha,10)}"

    @discord.ui.button(label="✅ Evet", style=discord.ButtonStyle.success)
    async def evet(self, interaction, button):
        if not yetkili_mi(interaction.user):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
        self.oylar[interaction.user.id] = True
        emb = interaction.message.embeds[0]; emb.set_field_at(-1, name="📊 Oylar", value=self.oy_bar())
        await interaction.response.edit_message(embed=emb, view=self)

    @discord.ui.button(label="❌ Hayır", style=discord.ButtonStyle.danger)
    async def hayir(self, interaction, button):
        if not yetkili_mi(interaction.user):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
        self.oylar[interaction.user.id] = False
        emb = interaction.message.embeds[0]; emb.set_field_at(-1, name="📊 Oylar", value=self.oy_bar())
        await interaction.response.edit_message(embed=emb, view=self)

    # ── DÜZELTME: defer + edit_original_response ──────────────
    @discord.ui.button(label="🔒 Oyu Kapat & Uygula", style=discord.ButtonStyle.secondary)
    async def kapat(self, interaction, button):
        if not yetkili_mi(interaction.user):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return

        await interaction.response.defer()  # ← 3 sn timeout'u önler

        ev = sum(1 for v in self.oylar.values() if v)
        ha = sum(1 for v in self.oylar.values() if not v)
        hedef = interaction.guild.get_member(self.hedef_id)
        kabul = ev > ha
        if hedef and kabul:
            data = load_data(); md = get_md(data, hedef.id)
            eski = md.get("rutbe")
            md["rutbe"] = self.yeni_rutbe
            md["terfi_gecmisi"].append({"tarih": now_iso(), "eski_rutbe": self.eski_rutbe,
                                        "yeni_rutbe": self.yeni_rutbe, "evet": ev, "hayir": ha,
                                        "onaylayan": str(interaction.user), "tip": "terfi"})
            gecmis_kaydet(md, "Terfi Edildi", f"{self.eski_rutbe} → {self.yeni_rutbe}", str(interaction.user))
            save_data(data)
            await rutbe_rol_guncelle(hedef, eski, self.yeni_rutbe)
            await dm_bildirim(hedef, "Terfi Edildiniz! 🎉",
                              f"{self.eski_rutbe} → **{self.yeni_rutbe}**", str(interaction.user))
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green() if kabul else discord.Color.red()
        emb.title = f"🎖️ Terfi — {'✅ KABUL' if kabul else '❌ REDDEDİLDİ'}"
        emb.set_field_at(-1, name="📊 Final", value=self.oy_bar())
        self.stop()
        for item in self.children: item.disabled = True
        await interaction.edit_original_response(embed=emb, view=self)  # ← defer sonrası bunu kullan

# ══════════════════════════════════════════
#  SEBEP DROPDOWN
# ══════════════════════════════════════════
class SebepDropdown(discord.ui.Select):
    def __init__(self, islem_tipi, hedef, seviye=0):
        self.islem_tipi = islem_tipi; self.hedef = hedef; self.seviye = seviye
        super().__init__(placeholder="📋 Sebep seçin...",
                         options=[discord.SelectOption(label=s, value=s) for s in SEBEP_SABLONLARI])

    async def callback(self, interaction):
        view: SebepView = self.view
        if self.values[0] == "Diğer (Açıklayınız)":
            async def modal_cb(inter, s): await view.islemi_uygula(inter, s)
            await interaction.response.send_modal(SebepModal(modal_cb))
        else:
            await view.islemi_uygula(interaction, self.values[0])

class SebepView(discord.ui.View):
    def __init__(self, islem_tipi, hedef, yapan, seviye=0):
        super().__init__(timeout=120)
        self.islem_tipi = islem_tipi; self.hedef = hedef
        self.yapan = yapan; self.seviye = seviye
        self.add_item(SebepDropdown(islem_tipi, hedef, seviye))

    async def islemi_uygula(self, interaction, sebep):
        await interaction.response.defer()
        data = load_data(); md = get_md(data, self.hedef.id)
        islem_str = ""; renk = discord.Color.orange()
        if self.islem_tipi == "grev":
            md["grev"] = self.seviye
            await strike_rolleri_temizle(self.hedef)
            rol = interaction.guild.get_role({1: GREV_1_ROLE, 2: GREV_2_ROLE, 3: GREV_3_ROLE}[self.seviye])
            if rol: await self.hedef.add_roles(rol)
            islem_str = f"Strike {self.seviye} Verildi"; renk = discord.Color.red()
        elif self.islem_tipi == "ihrac":
            md["ihrac"] = True; md["grev"] = 3
            eski_rutbe = md.get("rutbe")
            await strike_rolleri_temizle(self.hedef)
            await rutbe_rol_guncelle(self.hedef, eski_rutbe, None)
            rol = interaction.guild.get_role(IHRAC_ROLE)
            if rol: await self.hedef.add_roles(rol)
            islem_str = "İhraç Edildi"; renk = discord.Color.dark_red()
        elif self.islem_tipi == "uzaklastir":
            md["aktif"] = False
            islem_str = "Görevden Uzaklaştırıldı"; renk = discord.Color.dark_gray()
        gecmis_kaydet(md, islem_str, sebep, str(interaction.user))
        save_data(data)
        await dm_bildirim(self.hedef, islem_str, sebep, str(interaction.user))
        await log_isle(interaction.guild, self.hedef, islem_str, sebep, interaction.user.mention, renk)
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md),
                                                 view=StrikePaneli(self.hedef, self.yapan))

# ══════════════════════════════════════════
#  ONAY VIEW
# ══════════════════════════════════════════
class OnayView(discord.ui.View):
    def __init__(self, islem_tipi, hedef, yapan, aciklama):
        super().__init__(timeout=60)
        self.islem_tipi = islem_tipi; self.hedef = hedef
        self.yapan = yapan; self.aciklama = aciklama

    async def interaction_check(self, interaction):
        if interaction.user.id != self.yapan.id:
            await interaction.response.send_message("❌ Sadece komutu açan kişi onaylayabilir.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Onayla", style=discord.ButtonStyle.danger)
    async def onayla(self, interaction, button):
        e = discord.Embed(title="📋 Sebep Seçin", description=self.aciklama, color=discord.Color.orange())
        await interaction.response.edit_message(embed=e, view=SebepView(self.islem_tipi, self.hedef, self.yapan))

    @discord.ui.button(label="❌ İptal", style=discord.ButtonStyle.secondary)
    async def iptal(self, interaction, button):
        data = load_data(); md = get_md(data, self.hedef.id)
        await interaction.response.edit_message(embed=durum_embed(self.hedef, md),
                                                 view=StrikePaneli(self.hedef, self.yapan))

# ══════════════════════════════════════════
#  NOT LİSTESİ VIEW
# ══════════════════════════════════════════
class NotListesiView(discord.ui.View):
    def __init__(self, hedef, yapan, sayfa=0):
        super().__init__(timeout=120)
        self.hedef = hedef; self.yapan = yapan; self.sayfa = sayfa

    def _embed(self):
        data = load_data(); md = get_md(data, self.hedef.id); notlar = md.get("not_listesi", [])
        e = discord.Embed(title=f"📝 {self.hedef.display_name} — Notlar", color=discord.Color.blurple())
        if not notlar: e.description = "Kayıtlı not yok."
        else:
            for n in notlar[self.sayfa*5:(self.sayfa+1)*5]:
                e.add_field(name=f"`{n['tarih'][:10]}` — {n['yapan']}", value=n["icerik"], inline=False)
        e.set_footer(text=f"Sayfa {self.sayfa+1} | Toplam {len(notlar)} not")
        return e

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def onceki(self, i, b):
        if self.sayfa > 0: self.sayfa -= 1
        await i.response.edit_message(embed=self._embed(), view=NotListesiView(self.hedef, self.yapan, self.sayfa))

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def sonraki(self, i, b):
        data = load_data(); md = get_md(data, self.hedef.id)
        if (self.sayfa+1)*5 < len(md.get("not_listesi", [])): self.sayfa += 1
        await i.response.edit_message(embed=self._embed(), view=NotListesiView(self.hedef, self.yapan, self.sayfa))

    @discord.ui.button(label="🔙 Geri", style=discord.ButtonStyle.secondary)
    async def geri(self, i, b):
        data = load_data(); md = get_md(data, self.hedef.id)
        await i.response.edit_message(embed=durum_embed(self.hedef, md), view=StrikePaneli(self.hedef, self.yapan))

# ══════════════════════════════════════════
#  TERFİ RÜTBE DROPDOWN
# ══════════════════════════════════════════
class TerfiRutbeDropdown(discord.ui.Select):
    def __init__(self, hedef, yapan):
        self.hedef = hedef; self.yapan = yapan
        super().__init__(placeholder="📈 Yeni rütbe seç...",
                         options=[discord.SelectOption(label=r, value=r) for r in RUTBE_SIRASI])

    async def callback(self, interaction):
        await interaction.response.defer()
        yeni = self.values[0]
        data = load_data(); md = get_md(data, self.hedef.id)
        eski = md.get("rutbe") or "Belirsiz"
        e = discord.Embed(title="🎖️ Terfi Oylaması",
                          description=f"{self.hedef.mention} için terfi oylaması.",
                          color=discord.Color.gold(), timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=self.hedef.display_avatar.url)
        e.add_field(name="👤 Üye",         value=self.hedef.mention,       inline=True)
        e.add_field(name="📉 Mevcut",      value=eski,                     inline=True)
        e.add_field(name="📈 Yeni",        value=yeni,                     inline=True)
        e.add_field(name="👮 Teklif Eden", value=interaction.user.mention, inline=True)
        e.add_field(name="📊 Oylar",       value="Henüz oy yok",           inline=False)
        e.set_footer(text="SASP Terfi Sistemi | Yetkililerin oyu bekleniyor...")
        oy_view = TerfiOyView(self.hedef.id, yeni, eski)
        msg = await kanal_gonder(interaction.guild, TERFI_KANAL_ID, e, oy_view)
        if msg:
            gecmis_kaydet(md, "Terfi Oylaması Başlatıldı", f"{eski} → {yeni}", str(interaction.user))
            save_data(data)
        else:
            md["rutbe"] = yeni
            md["terfi_gecmisi"].append({"tarih": now_iso(), "eski_rutbe": eski, "yeni_rutbe": yeni,
                                        "onaylayan": str(interaction.user), "tip": "terfi"})
            gecmis_kaydet(md, "Terfi Edildi", f"{eski} → {yeni}", str(interaction.user))
            save_data(data)
            await rutbe_rol_guncelle(self.hedef, eski, yeni)
            await dm_bildirim(self.hedef, "Terfi Edildiniz! 🎉", f"{eski} → **{yeni}**", str(interaction.user))
            await log_isle(interaction.guild, self.hedef, "Terfi Edildi", f"{eski} → {yeni}",
                           interaction.user.mention, discord.Color.gold())
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md),
                                                 view=TerfiPaneli(self.hedef, self.yapan))

class TerfiRutbeView(discord.ui.View):
    def __init__(self, hedef, yapan):
        super().__init__(timeout=60); self.add_item(TerfiRutbeDropdown(hedef, yapan))

# ══════════════════════════════════════════
#  RÜTBE DÜŞÜR DROPDOWN
# ══════════════════════════════════════════
class RutbeDusurDropdown(discord.ui.Select):
    def __init__(self, hedef, yapan):
        self.hedef = hedef; self.yapan = yapan
        super().__init__(placeholder="📉 Düşürülecek rütbeyi seç...",
                         options=[discord.SelectOption(label=r, value=r) for r in RUTBE_SIRASI])

    async def callback(self, interaction):
        yeni = self.values[0]
        data = load_data(); md = get_md(data, self.hedef.id)
        eski = md.get("rutbe") or "Belirsiz"
        if eski in RUTBE_SIRASI and yeni in RUTBE_SIRASI:
            if RUTBE_SIRASI.index(yeni) >= RUTBE_SIRASI.index(eski):
                await interaction.response.send_message(
                    f"❌ **{yeni}** rütbesi **{eski}** rütbesinden düşük değil!",
                    ephemeral=True); return
        await interaction.response.defer()
        md["rutbe"] = yeni
        md["terfi_gecmisi"].append({"tarih": now_iso(), "eski_rutbe": eski, "yeni_rutbe": yeni,
                                    "onaylayan": str(interaction.user), "tip": "düşürme"})
        gecmis_kaydet(md, "Rütbe Düşürüldü", f"{eski} → {yeni}", str(interaction.user))
        save_data(data)
        await rutbe_rol_guncelle(self.hedef, eski, yeni)
        await dm_bildirim(self.hedef, "Rütbeniz Düşürüldü 📉", f"{eski} → {yeni}", str(interaction.user))
        await log_isle(interaction.guild, self.hedef, "Rütbe Düşürüldü",
                       f"{eski} → {yeni}", interaction.user.mention, discord.Color.dark_orange())
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md),
                                                 view=TerfiPaneli(self.hedef, self.yapan))

class RutbeDusurView(discord.ui.View):
    def __init__(self, hedef, yapan):
        super().__init__(timeout=60); self.add_item(RutbeDusurDropdown(hedef, yapan))

# ══════════════════════════════════════════
#  NÖBET BÖLGE DROPDOWN
# ══════════════════════════════════════════
class NobetBolgeDropdown(discord.ui.Select):
    def __init__(self, hedef, yapan):
        self.hedef = hedef; self.yapan = yapan
        super().__init__(placeholder="📍 Nöbet bölgesi seç...",
                         options=[discord.SelectOption(label=b, value=b) for b in NOBET_BOLGELER])

    async def callback(self, interaction):
        await interaction.response.defer()
        bolge = self.values[0]
        data = load_data(); md = get_md(data, self.hedef.id)
        md["aktif_nobet"] = {"bolge": bolge, "baslangic": now_iso(), "baslatan": str(interaction.user)}
        gecmis_kaydet(md, "Nöbet Başladı", f"Bölge: {bolge}", str(interaction.user))
        save_data(data)
        await dm_bildirim(self.hedef, "Nöbet Başlatıldı 🚔", f"Bölge: {bolge}", str(interaction.user))
        await log_isle(interaction.guild, self.hedef, "Nöbet Başladı", f"Bölge: {bolge}",
                       interaction.user.mention, discord.Color.blue())
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md),
                                                 view=NobetPaneli(self.hedef, self.yapan))

class NobetBolgeView(discord.ui.View):
    def __init__(self, hedef, yapan):
        super().__init__(timeout=60); self.add_item(NobetBolgeDropdown(hedef, yapan))

# ══════════════════════════════════════════
#  ÜYE SEÇİM
# ══════════════════════════════════════════
class UyeSecimDropdown(discord.ui.UserSelect):
    def __init__(self, yapan, sonraki_panel_cls):
        super().__init__(placeholder="👤 Üye seç...", min_values=1, max_values=1)
        self.yapan = yapan; self.sonraki_panel_cls = sonraki_panel_cls

    async def callback(self, interaction):
        hedef = self.values[0]
        if hedef.bot:
            await interaction.response.send_message("❌ Botlara işlem yapamazsınız.", ephemeral=True); return
        data = load_data(); md = get_md(data, hedef.id); save_data(data)
        await interaction.response.edit_message(embed=durum_embed(hedef, md),
                                                 view=self.sonraki_panel_cls(hedef, self.yapan))

class UyeSecimView(discord.ui.View):
    def __init__(self, yapan, sonraki_panel_cls):
        super().__init__(timeout=120)
        self.add_item(UyeSecimDropdown(yapan, sonraki_panel_cls))

    async def interaction_check(self, interaction):
        if not yetkili_mi(interaction.user):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return False
        return True

# ══════════════════════════════════════════
#  PANEL BASE CLASS
# ══════════════════════════════════════════
class YetkiliPanel(discord.ui.View):
    def __init__(self, hedef, yapan, timeout=300):
        super().__init__(timeout=timeout)
        self.hedef = hedef; self.yapan = yapan

    async def interaction_check(self, interaction):
        if interaction.user.id != self.yapan.id:
            await interaction.response.send_message("❌ Bu paneli sadece açan kişi kullanabilir.", ephemeral=True)
            return False
        if not yetkili_mi(interaction.user):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True)
            return False
        return True

# ══════════════════════════════════════════
#  1️⃣  STRİKE PANELİ
# ══════════════════════════════════════════
class StrikePaneli(YetkiliPanel):
    async def _grev(self, interaction, seviye):
        data = load_data(); md = get_md(data, self.hedef.id)
        if md["ihrac"]:
            await interaction.response.send_message("❌ Üye zaten ihraç edilmiş.", ephemeral=True); return
        e = discord.Embed(title="📋 Sebep Seçin",
                          description=f"**{self.hedef.display_name}** → Strike {seviye}",
                          color=discord.Color.orange())
        await interaction.response.edit_message(embed=e, view=SebepView("grev", self.hedef, self.yapan, seviye))

    @discord.ui.button(label="1X Strike", style=discord.ButtonStyle.secondary, emoji="⚠️", row=0)
    async def g1(self, i, b): await self._grev(i, 1)
    @discord.ui.button(label="2X Strike", style=discord.ButtonStyle.primary,   emoji="⚠️", row=0)
    async def g2(self, i, b): await self._grev(i, 2)
    @discord.ui.button(label="3X Strike", style=discord.ButtonStyle.danger,    emoji="🚨", row=0)
    async def g3(self, i, b): await self._grev(i, 3)

    @discord.ui.button(label="Sıfırla", style=discord.ButtonStyle.success, emoji="🔄", row=0)
    async def sifirla(self, interaction, button):
        await interaction.response.defer()
        data = load_data(); md = get_md(data, self.hedef.id)
        md["grev"] = 0; md["ihrac"] = False
        await strike_rolleri_temizle(self.hedef)
        gecmis_kaydet(md, "Kayıt Sıfırlandı", "Manuel sıfırlama", str(interaction.user)); save_data(data)
        await dm_bildirim(self.hedef, "Kayıt Sıfırlandı", "Manuel sıfırlama", str(interaction.user))
        await log_isle(interaction.guild, self.hedef, "Kayıt Sıfırlandı", "Manuel sıfırlama",
                       interaction.user.mention, discord.Color.green())
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md), view=self)

    @discord.ui.button(label="İHRAÇ ET", style=discord.ButtonStyle.danger, emoji="🔴", row=1)
    async def ihrac(self, interaction, button):
        data = load_data(); md = get_md(data, self.hedef.id)
        if md["ihrac"]:
            await interaction.response.send_message("❌ Zaten ihraç edilmiş.", ephemeral=True); return
        e = discord.Embed(title="⚠️ İhraç Onayı",
                          description=f"{self.hedef.mention} ihraç edilecek. Emin misiniz?",
                          color=discord.Color.dark_red())
        await interaction.response.edit_message(embed=e,
            view=OnayView("ihrac", self.hedef, self.yapan, f"**{self.hedef.display_name}** ihraç sebebi:"))

    @discord.ui.button(label="İhracı Kaldır", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def ihrac_kaldir(self, interaction, button):
        await interaction.response.defer()
        data = load_data(); md = get_md(data, self.hedef.id)
        md["ihrac"] = False; md["grev"] = 0
        await strike_rolleri_temizle(self.hedef)
        gecmis_kaydet(md, "İhraç Kaldırıldı", "Panel üzerinden", str(interaction.user)); save_data(data)
        await dm_bildirim(self.hedef, "İhraç Kaldırıldı", "Panel üzerinden", str(interaction.user))
        await log_isle(interaction.guild, self.hedef, "İhraç Kaldırıldı", "Panel üzerinden",
                       interaction.user.mention, discord.Color.green())
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md), view=self)

    @discord.ui.button(label="Uzaklaştır", style=discord.ButtonStyle.danger, emoji="⛔", row=1)
    async def uzaklastir(self, interaction, button):
        data = load_data(); md = get_md(data, self.hedef.id)
        if not md.get("aktif", True):
            await interaction.response.send_message("❌ Zaten uzaklaştırılmış.", ephemeral=True); return
        e = discord.Embed(title="⛔ Uzaklaştırma Onayı",
                          description=f"{self.hedef.mention} uzaklaştırılacak.", color=discord.Color.dark_gray())
        await interaction.response.edit_message(embed=e,
            view=OnayView("uzaklastir", self.hedef, self.yapan, f"**{self.hedef.display_name}** uzaklaştırma sebebi:"))

    @discord.ui.button(label="Göreve Al", style=discord.ButtonStyle.success, emoji="🟢", row=1)
    async def goreve_al(self, interaction, button):
        await interaction.response.defer()
        data = load_data(); md = get_md(data, self.hedef.id)
        md["aktif"] = True
        gecmis_kaydet(md, "Göreve Alındı", "Panel üzerinden", str(interaction.user)); save_data(data)
        await dm_bildirim(self.hedef, "Göreve Alındı", "Panel üzerinden", str(interaction.user))
        await log_isle(interaction.guild, self.hedef, "Göreve Alındı", "Panel üzerinden",
                       interaction.user.mention, discord.Color.green())
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md), view=self)

    @discord.ui.button(label="📝 Not Ekle", style=discord.ButtonStyle.secondary, row=2)
    async def not_ekle(self, i, b): await i.response.send_modal(NotModal(self.hedef, self.yapan))
    @discord.ui.button(label="📋 Notlar",   style=discord.ButtonStyle.secondary, row=2)
    async def notlar(self, interaction, button):
        v = NotListesiView(self.hedef, self.yapan)
        await interaction.response.edit_message(embed=v._embed(), view=v)
    @discord.ui.button(label="🪪 Profil",   style=discord.ButtonStyle.secondary, row=2)
    async def profil(self, i, b): await i.response.send_modal(ProfilModal(self.hedef, self.yapan))
    @discord.ui.button(label="📜 Geçmiş",  style=discord.ButtonStyle.secondary, row=2)
    async def gecmis_btn(self, interaction, button):
        data = load_data(); md = get_md(data, self.hedef.id); g = md["gecmis"]
        e = discord.Embed(title=f"📜 {self.hedef.display_name} — Geçmiş", color=discord.Color.blurple())
        e.set_thumbnail(url=self.hedef.display_avatar.url)
        if not g: e.description = "Kayıt bulunamadı."
        else:
            for k in g[-10:][::-1]:
                e.add_field(name=f"`{k['tarih'][:10]}` {k['islem']}", value=f"📋 {k['sebep']}\n👤 {k['yapan']}", inline=False)
        e.set_footer(text=f"Son 10 | Toplam {len(g)}")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="🔙 Ana Menü", style=discord.ButtonStyle.secondary, row=3)
    async def geri(self, interaction, button):
        await interaction.response.edit_message(embed=ana_menu_embed(), view=AnaMenuView(self.yapan))

# ══════════════════════════════════════════
#  2️⃣  NÖBET PANELİ
# ══════════════════════════════════════════
class NobetPaneli(YetkiliPanel):
    @discord.ui.button(label="🚔 Nöbet Başlat", style=discord.ButtonStyle.primary, row=0)
    async def nobet_baslat(self, interaction, button):
        data = load_data(); md = get_md(data, self.hedef.id)
        if md.get("aktif_nobet"):
            await interaction.response.send_message("❌ Zaten aktif nöbet var.", ephemeral=True); return
        e = discord.Embed(title="🚔 Nöbet Bölgesi Seç",
                          description=f"**{self.hedef.display_name}** için bölge seçin.", color=discord.Color.blue())
        await interaction.response.edit_message(embed=e, view=NobetBolgeView(self.hedef, self.yapan))

    @discord.ui.button(label="🏁 Nöbet Bitir", style=discord.ButtonStyle.danger, row=0)
    async def nobet_bitir(self, interaction, button):
        await interaction.response.defer()
        data = load_data(); md = get_md(data, self.hedef.id)
        if not md.get("aktif_nobet"):
            await interaction.followup.send("❌ Aktif nöbet yok.", ephemeral=True); return
        nb = md["aktif_nobet"]
        sure = int((datetime.now(timezone.utc) - datetime.fromisoformat(nb["baslangic"])).total_seconds() / 60)
        nb["bitis"] = now_iso(); nb["sure_dakika"] = sure
        md["nobet_gecmisi"].append(nb); md["aktif_nobet"] = None
        gecmis_kaydet(md, "Nöbet Bitti", f"{nb['bolge']} | {sure} dk", str(interaction.user)); save_data(data)
        await dm_bildirim(self.hedef, "Nöbet Sona Erdi 🏁", f"{nb['bolge']} | {sure} dk", str(interaction.user))
        await log_isle(interaction.guild, self.hedef, "Nöbet Bitti", f"{nb['bolge']} | {sure} dk",
                       interaction.user.mention, discord.Color.blue())
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md), view=self)

    @discord.ui.button(label="🔙 Ana Menü", style=discord.ButtonStyle.secondary, row=1)
    async def geri(self, interaction, button):
        await interaction.response.edit_message(embed=ana_menu_embed(), view=AnaMenuView(self.yapan))

# ══════════════════════════════════════════
#  3️⃣  TERFİ PANELİ
# ══════════════════════════════════════════
class TerfiPaneli(YetkiliPanel):
    @discord.ui.button(label="📈 Rütbe Yükselt", style=discord.ButtonStyle.success, row=0)
    async def terfi_teklif(self, interaction, button):
        e = discord.Embed(title="📈 Rütbe Yükselt",
                          description=f"**{self.hedef.display_name}** için yeni rütbe seçin:",
                          color=discord.Color.gold())
        await interaction.response.edit_message(embed=e, view=TerfiRutbeView(self.hedef, self.yapan))

    @discord.ui.button(label="📉 Rütbe Düşür", style=discord.ButtonStyle.danger, row=0)
    async def rutbe_dusur(self, interaction, button):
        data = load_data(); md = get_md(data, self.hedef.id)
        mevcut = md.get("rutbe") or "Belirsiz"
        e = discord.Embed(title="📉 Rütbe Düşür",
                          description=f"**{self.hedef.display_name}** — Mevcut: **{mevcut}**\nDüşürülecek rütbeyi seçin:",
                          color=discord.Color.dark_orange())
        await interaction.response.edit_message(embed=e, view=RutbeDusurView(self.hedef, self.yapan))

    @discord.ui.button(label="📜 Terfi Geçmişi", style=discord.ButtonStyle.secondary, row=0)
    async def terfi_gecmis(self, interaction, button):
        data = load_data(); md = get_md(data, self.hedef.id); terfiler = md.get("terfi_gecmisi", [])
        e = discord.Embed(title=f"🎖️ {self.hedef.display_name} — Rütbe Geçmişi", color=discord.Color.gold())
        e.set_thumbnail(url=self.hedef.display_avatar.url)
        if md.get("rutbe"): e.add_field(name="Mevcut Rütbe", value=md["rutbe"], inline=False)
        if not terfiler: e.description = "Kayıtlı rütbe değişikliği yok."
        else:
            for t in terfiler[::-1]:
                tip = t.get("tip", "terfi")
                emoji = "📈" if tip == "terfi" else "📉"
                e.add_field(name=f"`{t['tarih'][:10]}` {emoji} {t.get('eski_rutbe','?')} → {t['yeni_rutbe']}",
                            value=f"👮 {t.get('onaylayan','?')}", inline=False)
        e.set_footer(text=f"Toplam {len(terfiler)} değişiklik | SASP")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="🔙 Ana Menü", style=discord.ButtonStyle.secondary, row=1)
    async def geri(self, interaction, button):
        await interaction.response.edit_message(embed=ana_menu_embed(), view=AnaMenuView(self.yapan))

# ══════════════════════════════════════════
#  4️⃣  İZİN PANELİ
# ══════════════════════════════════════════
class IzinPaneli(YetkiliPanel):
    @discord.ui.button(label="✅ İzin Ver", style=discord.ButtonStyle.success, row=0)
    async def izin_ver(self, interaction, button):
        async def cb(inter, s):
            await inter.response.defer()
            data = load_data(); md = get_md(data, self.hedef.id)
            bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            md["aktif_izin"] = {"baslangic": bugun, "bitis": "Belirsiz", "sebep": s, "onaylayan": str(inter.user)}
            md["izin_gecmisi"].append({**md["aktif_izin"], "tarih": now_iso(), "durum": "onaylandi"})
            gecmis_kaydet(md, "İzin Verildi", s, str(inter.user)); save_data(data)
            await dm_bildirim(self.hedef, "İzin Onaylandı ✅", s, str(inter.user))
            await log_isle(inter.guild, self.hedef, "İzin Verildi", s, inter.user.mention, discord.Color.teal())
            await inter.edit_original_response(embed=durum_embed(self.hedef, md), view=self)
        await interaction.response.send_modal(SebepModal(cb))

    @discord.ui.button(label="🏁 İzni Bitir", style=discord.ButtonStyle.danger, row=0)
    async def izin_bitir(self, interaction, button):
        await interaction.response.defer()
        data = load_data(); md = get_md(data, self.hedef.id)
        if not md.get("aktif_izin"):
            await interaction.followup.send("❌ Aktif izin yok.", ephemeral=True); return
        md["aktif_izin"] = None
        gecmis_kaydet(md, "İzin Sona Erdi", "Yetkilice sonlandırıldı", str(interaction.user)); save_data(data)
        await dm_bildirim(self.hedef, "İzniniz Sona Erdi", "Yetkilice sonlandırıldı", str(interaction.user))
        await log_isle(interaction.guild, self.hedef, "İzin Sona Erdi", "Yetkilice sonlandırıldı",
                       interaction.user.mention, discord.Color.orange())
        await interaction.edit_original_response(embed=durum_embed(self.hedef, md), view=self)

    @discord.ui.button(label="🔙 Ana Menü", style=discord.ButtonStyle.secondary, row=1)
    async def geri(self, interaction, button):
        await interaction.response.edit_message(embed=ana_menu_embed(), view=AnaMenuView(self.yapan))

# ══════════════════════════════════════════
#  ANA MENÜ
# ══════════════════════════════════════════
class AnaMenuDropdown(discord.ui.Select):
    def __init__(self, yapan):
        self.yapan = yapan
        super().__init__(
            placeholder="📌 Ne yapmak istiyorsunuz?",
            options=[
                discord.SelectOption(label="👮 Üye Yönetimi",   value="yonetim",    description="Strike, ihraç, profil, notlar",     emoji="👮"),
                discord.SelectOption(label="🚔 Nöbet İşlemleri", value="nobet",      description="Nöbet başlat/bitir, aktif nöbetler", emoji="🚔"),
                discord.SelectOption(label="🎖️ Terfi Sistemi",   value="terfi",      description="Rütbe yükselt/düşür, geçmiş",       emoji="🎖️"),
                discord.SelectOption(label="🏖️ İzin Sistemi",    value="izin",       description="İzin talebi, izin ver/bitir",        emoji="🏖️"),
                discord.SelectOption(label="🚨 Rapor / Şikayet", value="rapor",      description="Bir üyeyi yetkililere şikayet et",   emoji="🚨"),
                discord.SelectOption(label="📊 İstatistikler",   value="istatistik", description="Sunucu genel istatistikleri",        emoji="📊"),
                discord.SelectOption(label="⚠️ Aktif Strikeler", value="strikeler",  description="Strikeli ve ihraçlı üyeler",         emoji="⚠️"),
                discord.SelectOption(label="🚔 Aktif Nöbetler",  value="nobetler",   description="Şu an nöbette olan üyeler",          emoji="🚔"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        s = self.values[0]
        yetki = yetkili_mi(interaction.user)

        if s == "yonetim":
            if not yetki: await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
            e = discord.Embed(title="👮 Üye Yönetimi", description="İşlem yapılacak üyeyi seçin.", color=discord.Color.blurple())
            await interaction.response.edit_message(embed=e, view=UyeSecimView(self.yapan, StrikePaneli))

        elif s == "nobet":
            if not yetki: await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
            e = discord.Embed(title="🚔 Nöbet İşlemleri", description="Üyeyi seçin.", color=discord.Color.blue())
            await interaction.response.edit_message(embed=e, view=UyeSecimView(self.yapan, NobetPaneli))

        elif s == "terfi":
            if not yetki: await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
            e = discord.Embed(title="🎖️ Terfi Sistemi", description="Rütbe değişikliği yapılacak üyeyi seçin.", color=discord.Color.gold())
            await interaction.response.edit_message(embed=e, view=UyeSecimView(self.yapan, TerfiPaneli))

        elif s == "izin":
            e = discord.Embed(title="🏖️ İzin Sistemi",
                              description="**Üye:** İzin talebi oluşturabilirsiniz.\n**Yetkili:** Üye seçip doğrudan izin verebilirsiniz.",
                              color=discord.Color.teal())
            await interaction.response.edit_message(embed=e, view=IzinMenuView(self.yapan))

        elif s == "rapor":
            await interaction.response.send_modal(RaporModal(interaction.user))

        elif s == "istatistik":
            if not yetki: await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
            data = load_data()
            s1=s2=s3=ih=temiz=uzak=0
            for md in data.values():
                if not isinstance(md, dict): continue
                if md.get("ihrac"):            ih+=1
                elif not md.get("aktif",True): uzak+=1
                elif md.get("grev")==3:        s3+=1
                elif md.get("grev")==2:        s2+=1
                elif md.get("grev")==1:        s1+=1
                else:                          temiz+=1
            toplam   = sum(len(md.get("gecmis",[])) for md in data.values() if isinstance(md,dict))
            nobetler = sum(1 for md in data.values() if isinstance(md,dict) and md.get("aktif_nobet"))
            izinler  = sum(1 for md in data.values() if isinstance(md,dict) and md.get("aktif_izin"))
            e = discord.Embed(title="📊 SASP — İstatistikler", color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
            e.add_field(name="👥 Kayıtlı",         value=f"`{len([m for m in data.values() if isinstance(m,dict)])}`", inline=True)
            e.add_field(name="✅ Temiz",            value=f"`{temiz}`",    inline=True)
            e.add_field(name="⛔ Uzaklaştırılmış",  value=f"`{uzak}`",     inline=True)
            e.add_field(name="⚠️ Strike 1",        value=f"`{s1}`",       inline=True)
            e.add_field(name="⚠️ Strike 2",        value=f"`{s2}`",       inline=True)
            e.add_field(name="🚨 Strike 3",        value=f"`{s3}`",       inline=True)
            e.add_field(name="🔴 İhraç",           value=f"`{ih}`",       inline=True)
            e.add_field(name="🚔 Aktif Nöbet",     value=f"`{nobetler}`", inline=True)
            e.add_field(name="🏖️ Aktif İzin",      value=f"`{izinler}`",  inline=True)
            e.add_field(name="📋 Toplam İşlem",    value=f"`{toplam}`",   inline=True)
            e.set_footer(text="SASP Yönetim Sistemi | with by elgamex")
            await interaction.response.edit_message(embed=e, view=GeriView(self.yapan))

        elif s == "strikeler":
            if not yetki: await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
            data = load_data()
            e = discord.Embed(title="🚨 Aktif Strike / İhraç", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
            bulunan = False
            for uid, md in data.items():
                if not isinstance(md, dict): continue
                grev=md.get("grev",0); ihrac=md.get("ihrac",False)
                if grev==0 and not ihrac: continue
                member = interaction.guild.get_member(int(uid))
                isim = member.display_name if member else f"ID:{uid}"
                durum = "🔴 İHRAÇ" if ihrac else f"⚠️ Strike {grev}/3"
                son = md["gecmis"][-1]["tarih"][:10] if md["gecmis"] else "—"
                e.add_field(name=isim, value=f"{durum} | `{son}`", inline=False); bulunan=True
            if not bulunan: e.description = "✅ Aktif strike veya ihraç yok."
            e.set_footer(text="SASP Yönetim Sistemi | with by elgamex")
            await interaction.response.edit_message(embed=e, view=GeriView(self.yapan))

        elif s == "nobetler":
            if not yetki: await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
            data = load_data()
            e = discord.Embed(title="🚔 Aktif Nöbetler", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))
            bulunan = False
            for uid, md in data.items():
                if not isinstance(md,dict) or not md.get("aktif_nobet"): continue
                nb=md["aktif_nobet"]; member=interaction.guild.get_member(int(uid))
                isim=member.display_name if member else f"ID:{uid}"
                e.add_field(name=isim, value=f"📍 {nb['bolge']}\n⏰ {nb['baslangic'][:16].replace('T',' ')}", inline=True)
                bulunan=True
            if not bulunan: e.description = "Aktif nöbet bulunmuyor."
            e.set_footer(text="SASP Yönetim Sistemi | with by elgamex")
            await interaction.response.edit_message(embed=e, view=GeriView(self.yapan))


class AnaMenuView(discord.ui.View):
    def __init__(self, yapan):
        super().__init__(timeout=180)
        self.add_item(AnaMenuDropdown(yapan))

class GeriView(discord.ui.View):
    def __init__(self, yapan):
        super().__init__(timeout=120); self.yapan = yapan
    @discord.ui.button(label="🔙 Ana Menü", style=discord.ButtonStyle.secondary)
    async def geri(self, interaction, button):
        await interaction.response.edit_message(embed=ana_menu_embed(), view=AnaMenuView(self.yapan))

# ══════════════════════════════════════════
#  İZİN MENÜ VIEW
# ══════════════════════════════════════════
class IzinMenuView(discord.ui.View):
    def __init__(self, yapan):
        super().__init__(timeout=120); self.yapan = yapan

    @discord.ui.button(label="📝 İzin Talebi Oluştur", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def talep(self, interaction, button):
        await interaction.response.send_modal(IzinTalebiModal(interaction.user))

    @discord.ui.button(label="👮 İzin Ver / Bitir (Yetkili)", style=discord.ButtonStyle.success, emoji="✅", row=0)
    async def izin_yonetim(self, interaction, button):
        if not yetkili_mi(interaction.user):
            await interaction.response.send_message("❌ Yetkiniz yok.", ephemeral=True); return
        e = discord.Embed(title="🏖️ İzin Yönetimi", description="Üyeyi seçin.", color=discord.Color.teal())
        await interaction.response.edit_message(embed=e, view=UyeSecimView(self.yapan, IzinPaneli))

    @discord.ui.button(label="🔙 Ana Menü", style=discord.ButtonStyle.secondary, emoji="🔙", row=1)
    async def geri(self, interaction, button):
        await interaction.response.edit_message(embed=ana_menu_embed(), view=AnaMenuView(self.yapan))

# ══════════════════════════════════════════
#  TEK KOMUT: /sasp
# ══════════════════════════════════════════
@bot.tree.command(name="sasp", description="SASP Yönetim Sistemi")
async def sasp(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=ana_menu_embed(),
        view=AnaMenuView(interaction.user),
        ephemeral=True
    )

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅  {bot.user} aktif! | /sasp komutu aktif")
    print(f"🔑 Yetkili Rol ID: {YETKİLİ_ROL_ID}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="SASP | /sasp")
    )

@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = "❌ Yetkiniz yok." if isinstance(error, app_commands.MissingPermissions) else f"❌ Hata: {error}"
    try: await interaction.response.send_message(msg, ephemeral=True)
    except: await interaction.followup.send(msg, ephemeral=True)

bot.run(TOKEN)
