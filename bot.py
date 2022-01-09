from os import getenv
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
import re

import subapy
import discord
from discord.ext import tasks

from misc import book_name_mapping

# Load config
# with open('config.json') as f:
#     env(= getjson.loads().read())

settings = json.loads(open('settings.json').read())

regs_guilds = [927814722370301962]

# Load bot and DB
client = discord.Bot(intents=discord.Intents.all())
DB = subapy.AsyncClient(
    db_url=getenv('supabase_url'),
    api_key=getenv('subabase_api_key')
)

# Bot Events
@client.event
async def on_ready():
    DB.table = 'Tasks'
    await DB.update({"posted":False},subapy.Filter('id','eq',4))
    print('Logged in')
            
# Core Functions
clean_text = lambda raw_html: [i.strip().replace("\u3000","") for i in re.sub(re.compile('<.*?>'), '', raw_html).split("\n") if i not in ["","Bible Quote"]]

datetime_now = lambda: datetime.now(tz=ZoneInfo("Asia/Singapore"))

async def post_task(*, title, created_at, url, author, cell_group, description, **kwargs):
    title_embed = discord.Embed(
        title=title.title(),
        description=f"Created for: <t:{int(datetime.strptime(created_at,r'%Y-%m-%d').timestamp())}>\nAuthor: <@!{author}>",
        colour = discord.Colour.green()
    )
    embeds = [title_embed]
    response = requests.get(url)
    if response.status_code == 200:
        content = clean_text(response.text)
        book_name = {v:k for k,v in book_name_mapping.items()}[url.split("/")[3][14:]]
        passage_ref = f"{book_name.title()} {url[37:]}"
        if len(content) > 0:
            page = 1
            embed = discord.Embed(
                title=f"{title.title()}\n*{passage_ref}*",
                colour=discord.Colour.green()
            ).set_footer(text=f"{title.title()} | Page {page}")
            for verse in content:
                embed.add_field(name=re.findall(r"\d+:\d+",verse)[0], value=re.sub(re.compile(r"\d+:\d+"),"",verse), inline=False)
                if len(embed) > 5000:
                    page += 1
                    embeds.append(embed)
                    embed = discord.Embed(
                        title=title.title(),
                        colour = discord.Colour.green()
                    ).set_footer(text=f"{passage_ref.title()} | Page {page}")
            embeds.append(embed)
        
        # Post Content
        raw_channel = settings[cell_group]['reading_channel']
        channel = await client.fetch_channel(raw_channel)
        message = await channel.send(embeds=embeds)
        embed = discord.Embed(
            title="Mark as completed",
            description = f"React with ✅ to mark as completed here",
            colour = discord.Colour.teal()
        )
        content_msg = await channel.send(embed=embed)

        # Post Notification
        channel = await client.fetch_channel(settings[cell_group]['announcement_channel'])
        embed = discord.Embed(
            title=f"New Reading",
            description=f"Reading Title: {title.title()}\nCreated for: <t:{int(datetime.strptime(created_at,r'%Y-%m-%d').timestamp())}>\nAuthor: <@!{author}>\n",
            colour = discord.Colour.green()
        ).add_field(name="Description", value=description+f"\n[Jump to passage]({content_msg.jump_url})", inline=False)
        annoucement_msg = await channel.send(embed=embed)
        await annoucement_msg.add_reaction('✅')

        # Link Annoucement message
        embed = discord.Embed(
            title="Mark as completed",
            description=f"React with ✅ to mark as completed [here]({annoucement_msg.jump_url})",
            colour=discord.Colour.teal()
        )
        await content_msg.edit(embed=embed)
        return annoucement_msg.id
        
async def retrieve_tasks():
    now = datetime_now()
    DB.table = 'Tasks'
    tasks = await DB.read("*")
    for i in tasks:
        if i['created_at'] == now.strftime(r"%Y-%m-%d") and i['posted'] != True:
            print(f"Posting - {i['title']}")
            message_ref = await post_task(**i)
            await DB.update(i | {'posted': True, "post_details": str(message_ref)}, subapy.Filter('id', 'eq', i['id']))
    else:
        print("No tasks")

@client.event
async def on_raw_reaction_add(payload):
    emoji = payload.emoji.name
    message_id = payload.message_id
    channel_id = payload.channel_id
    user_id = payload.user_id
    member = payload.member

    if emoji == "✅" and member!=client.user:
        DB.table = 'Tasks'
        task = await DB.read(subapy.Filter('post_details','eq',str(message_id)))
        task = task[0]
        completed = {"users":task['completed']['users'] + [user_id]}    
        await DB.update(task.update(completed), subapy.Filter('post_details', 'eq', str(message_id)))

        cur_channel = await client.fetch_channel(channel_id)
        annoucement_msg = await cur_channel.fetch_message(message_id)
        embed = discord.Embed(
            title="New Reading",
            description=f"Reading Title: {task['title'].title()}\nCreated for: <t:{int(datetime.strptime(task['created_at'],r'%Y-%m-%d').timestamp())}>\nAuthor: <@!{task['author']}>",
            colour=discord.Colour.green()
        ).add_field(name="**Description**", value=task['description'], inline=False)
        _completed = len([member for member in member.guild.members if member.id in completed['users']])
        _total_users = len([member for member in member.guild.members if member.bot == False])
        completion_percentage = f"{_completed}/{_total_users} `{round((_completed/_total_users)*100,2)}%`"
        users_completion = [f"✅ {member}" if member.id in completed['users'] else f"❌ {member}" for member in member.guild.members]
        users_completion.remove("❌ Embeded#2449")
        users_completion = "\n".join(users_completion) if users_completion != [] else "No one has completed this task yet"
        embed.add_field(name=f'Completion Status: {completion_percentage}', value=users_completion, inline=False)
        await annoucement_msg.edit(embed=embed)

# Commands
# Book Name Autocomplete
async def book_name_autocomplete(ctx: discord.AutocompleteContext) -> list[str]:
    text = ctx.options['book'].lower()
    possible = []
    for book in book_name_mapping:
        if text in book.lower():
            possible.append(book)
    possible = ['Genesis'] if possible == [] else possible
    return possible

# Set Help
@client.command(name="help", aliases=["commands"])
async def help(ctx,command: discord.commands.Option(str,"Specific Command Name",required=False, choices=["setreading"], default="None")):
    if command == "None":
        embed = discord.Embed(
            title="Help",
            description="Commands: `setreading`",
            colour=discord.Colour.green()
        )
    elif command == "setreading":
        embed = discord.Embed(
            title="Set Reading",
            description='''
                Passage should be inthe format aa:bb - cc:dd
                1) aa = starting chapter
                2) bb = starting verse
                3) cc = ending chapter(May be omitted if it is the same as the starting chapter. The fomat will be "aa:bb-dd")
                4) dd = ending verse(May be omitted if there is only one verse. The fomat will be "aa:bb")"

                *Accepted Forms*
                24:1-25:20
                30:23-25
                3:16
                ''',
            colour=discord.Colour.green()
        )
    else:
        return
    await ctx.respond(embed=embed)

# Set Reading Command
@client.slash_command(
    guild_ids=regs_guilds,
    name='setreading',
    description='Set a reading for a future date',
    choices=['setreading <date> <url> <title> <description>'],
    permissions=[discord.commands.CommandPermission(id=929168912837410826, type=1, permission=True)]
)
async def new_read_cmd(
    ctx: discord.ApplicationContext,
    date: discord.commands.Option(str, 'Reading Date (Posts at Midnight), "tdy" "tmr". Format: [YY]/MM/DD (Year is Optional)', required=True),
    title: discord.commands.Option(str, 'Title of Reading', required=True),
    book: discord.commands.Option(str, 'Reference to the book name.',required=True, autocomplete=book_name_autocomplete),
    passage: discord.commands.Option(str, "In the format: aa:bb-cc:dd", required=True),
    cell_group: discord.commands.Option(str,"Cell Group. Defaults to the one related to this server", choices=list(settings.keys()), default="Auto", required=False),
    description: discord.commands.Option(str, 'Description of the reading', default="No Description", required=False)
):  
    embed = None
    if date == "tmr":
        date = (datetime_now()+timedelta(hours=24)).strftime(r"%Y/%m/%d")
    elif date == 'tdy':
        date = datetime_now().strftime(r"%Y/%m/%d")
    else:
        if re.search(r"\d{2}/\d{2}/\d{2}|\d{2}/\d{2}/\d{2}", date) == None:
            if re.search(r"\d{2}/\d{2}", date) == None:
                embed = discord.Embed(
                    title="Error",
                    description="Date format is invalid. Please use the format: [YY]/MM/DD (Year Defaults to this year)",
                    colour=discord.Colour.red()
                )
            else:
                date = f"{datetime_now().year}/{date}"

    if re.search(r'\d{1,3}:\d{1,3}-\d{1,3}:\d{1,3}|\d{1,3}:\d{1,3}|\d{1,3}:\d{1,3}-\d{1,3}', passage) == None:
        embed = discord.Embed(
            title="Error",
            description="Passage is not in the correct format.\nSee `/help setreading` for help",
            colour=discord.Colour.red()
        )
    if embed != None:
        await ctx.respond(embed=embed)
        return

    async with ctx.typing():
        book_code = book_name_mapping[book]
        processed_passage = f"http://ibibles.net/quote.php?cus-{book_code}/{passage}"
        cell_group = [i for i in settings if settings[i]['id'] == int(ctx.guild.id)][0] if cell_group == "Auto" else cell_group
        new_data = {
            "created_at": date,
            "title": title.title(),
            "url": processed_passage,
            "cell_group": cell_group,
            "description": description,
            "author" : str(ctx.author.id),
        }
        await DB.insert(new_data, subapy.Filter('created_at', 'eq', date), upsert=True)

        date = datetime.strptime(date, r'%Y/%m/%d')
        embed = discord.Embed(
            title="New Reading Created",
            description=f"Reading Title: {title.title()}\nCreated for: <t:{int(date.timestamp())}>\nAuthor: <@!{ctx.author.id}>",
            colour=discord.Colour.green()
        )
        embed.add_field(name=f"**{book} {passage}**", value=f"Read it [Here]({processed_passage})", inline=False)
        embed.add_field(name="Title", value=title, inline=False)
        embed.add_field(name="Description", value=description, inline=False)
        embed.set_footer(text="Bot by @Fishball_Noodles#7209")
    await ctx.respond(embed=embed)
    await retrieve_tasks()


@client.command(
    guild_ids=regs_guilds,
    name='forceretrieve',
    description='Force Retrieve Tasks and post',
    permissions=[discord.commands.CommandPermission(id=591107669180284928, type=2, permission=True)]
)
async def _force_retrieve_cmd(ctx: discord.ApplicationContext):
    await ctx.respond("Retrieving Tasks...")
    async with ctx.typing():
        await retrieve_tasks()
    await ctx.respond("Tasks Retrieved")

# Background tasks
# New Day Checker
@tasks.loop(seconds=5)
async def check_newday():
    await client.wait_until_ready()
    now=datetime_now()
    if now.hour == 0 and now.minute == 0:
        await retrieve_tasks()

# Start background tasks
check_newday.start()

# Start bot
client.run(getenv('discord_token'))