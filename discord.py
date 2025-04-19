import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# إعدادات البوت (يمكنك تعديلها)
TICKET_CATEGORY_NAME = "🎫 | التذاكر"
LOG_CHANNEL_NAME = "📜 | سجل-التذاكر"
STAFF_ROLE_NAME = "Staff"  # اسم رتبة الستاف
OWNER_ROLE_NAME = "Owner"  # اسم رتبة المالك

class TicketControl(View):
    def __init__(self, ticket_owner: discord.Member):
        super().__init__(timeout=None)
        self.ticket_owner = ticket_owner
        self.claimed = False
        self.claimed_by = None

    @discord.ui.button(label="استلام التذكرة", style=discord.ButtonStyle.green, custom_id="claim_ticket", emoji="🛄")
    async def claim(self, interaction: discord.Interaction, button: Button):
        if STAFF_ROLE_NAME not in [role.name for role in interaction.user.roles]:
            return await interaction.response.send_message("ليس لديك صلاحية استلام التذاكر!", ephemeral=True)
        
        if self.claimed:
            return await interaction.response.send_message(f"هذه التذكرة مستلمة بالفعل بواسطة {self.claimed_by.mention}", ephemeral=True)
        
        self.claimed = True
        self.claimed_by = interaction.user
        button.disabled = True
        button.style = discord.ButtonStyle.gray
        button.label = f"مستلمة بواسطة {interaction.user.name}"
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="تم الاستلام بواسطة", value=interaction.user.mention, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(f"تم استلام التذكرة بواسطة {interaction.user.mention}")

    @discord.ui.button(label="إغلاق التذكرة", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: Button):
        if STAFF_ROLE_NAME not in [role.name for role in interaction.user.roles]:
            return await interaction.response.send_message("ليس لديك صلاحية إغلاق التذاكر!", ephemeral=True)
        
        if not self.claimed:
            return await interaction.response.send_message("يجب استلام التذكرة أولاً قبل إغلاقها!", ephemeral=True)
        
        embed = discord.Embed(
            title="إغلاق التذكرة",
            description=f"تم إغلاق التذكرة بواسطة {interaction.user.mention}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        
        # تسجيل الإغلاق في سجل التذاكر
        log_channel = discord.utils.get(interaction.guild.channels, name=LOG_CHANNEL_NAME)
        if log_channel:
            log_embed = discord.Embed(
                title="تذكرة مغلقة",
                description=f"**بواسطة:** {interaction.user.mention}\n**المستلم:** {self.claimed_by.mention}\n**التذكرة:** {interaction.channel.name}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=log_embed)
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="إخطار المالك", style=discord.ButtonStyle.blurple, custom_id="ping_owner", emoji="👑")
    async def ping_owner(self, interaction: discord.Interaction, button: Button):
        if STAFF_ROLE_NAME not in [role.name for role in interaction.user.roles]:
            return await interaction.response.send_message("ليس لديك صلاحية إخطار المالك!", ephemeral=True)
        
        owner_role = discord.utils.get(interaction.guild.roles, name=OWNER_ROLE_NAME)
        if owner_role:
            await interaction.channel.send(f"{owner_role.mention} - تم طلب حضورك في هذه التذكرة")
            await interaction.response.send_message("تم إخطار المالك بنجاح!", ephemeral=True)
        else:
            await interaction.response.send_message("لم يتم العثور على رتبة المالك!", ephemeral=True)

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="الدعم الفني", emoji="🛠️", description="طلب مساعدة فنية"),
            discord.SelectOption(label="طلب تعويض", emoji="💰", description="في حالة طلب تعويض مالي"),
            discord.SelectOption(label="دعم الديسكورد", emoji="❓", description="استفسارات حول السيرفر"),
            discord.SelectOption(label="بلاغ ضد مخرب", emoji="🚨", description="الإبلاغ عن مخالفين")
        ]
        super().__init__(placeholder="اختر نوع التذكرة...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        await interaction.response.send_message(f"جارٍ إنشاء تذكرة {ticket_type}...", ephemeral=True)
        
        # إنشاء التذكرة
        category = discord.utils.get(interaction.guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            category = await interaction.guild.create_category(TICKET_CATEGORY_NAME, overwrites=overwrites)
        
        # إنشاء الروم (القناة)
        ticket_channel = await category.create_text_channel(
            name=f"{ticket_type}-{interaction.user.name}",
            topic=f"تذكرة {ticket_type} لـ {interaction.user}",
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True)
            }
        )
        
        # إرسال رسالة الترحيب
        embed = discord.Embed(
            title=f"تذكرة {ticket_type}",
            description=f"شكراً لك على فتح التذكرة!\n\n**المستخدم:** {interaction.user.mention}\n**النوع:** {ticket_type}\n\nسيقوم أحد أعضاء الفريق بالرد عليك قريباً.",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"بواسطة {interaction.user}", icon_url=interaction.user.avatar.url)
        
        control_view = TicketControl(interaction.user)
        await ticket_channel.send(
            content=f"{interaction.user.mention}",
            embed=embed,
            view=control_view
        )
        
        # تسجيل التذكرة
        log_channel = discord.utils.get(interaction.guild.channels, name=LOG_CHANNEL_NAME)
        if log_channel:
            log_embed = discord.Embed(
                title="تذكرة جديدة",
                description=f"**النوع:** {ticket_type}\n**المستخدم:** {interaction.user.mention}\n**التذكرة:** {ticket_channel.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=log_embed)

@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} is ready!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="التذاكر المفتوحة"))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    """إنشاء رسالة نظام التذاكر (للمشرفين فقط)"""
    embed = discord.Embed(
        title="نظام التذاكر",
        description="**اختر نوع التذكرة من القائمة أدناه:**\n\n"
                    "🛠️ الدعم الفني - للمساعدة التقنية\n"
                    "💰 طلب تعويض - لطلبات التعويض المالي\n"
                    "❓ دعم الديسكورد - لاستفسارات السيرفر\n"
                    "🚨 بلاغ ضد مخرب - للإبلاغ عن المخالفين",
        color=discord.Colour.blurple()
    )
    
    view = View()
    view.add_item(TicketSelect())
    
    await ctx.send(embed=embed, view=view)

bot.run("TOKEN_HERE")
