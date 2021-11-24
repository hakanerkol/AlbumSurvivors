from replit import db
from discord.ext import commands
import os
import operator
import discord
import requests

my_secret = os.environ['TOKEN']
bot = commands.Bot(command_prefix='$')

def get_metadata(mb_api):
  response = requests.get(mb_api)
  json_data = response.json()
  tracklist = []
  for dicts in json_data['media'][0]['tracks']:
    if 'title' in dicts:
        tracklist.append(dicts['title'])
  tracklist = [x.lower() for x in tracklist]
  return tracklist

def add_album(album_title, tracklist):
  split_title = album_title.split()
  acronym = ""
  for word in split_title:
    acronym += word[0]

  print(acronym)
  db[acronym] = album_title
  album_scores = {}

  for track in tracklist:
      album_scores[track] = 0

  db[album_title] = album_scores
  start_rounds = {album_title: 1}
  db['album_rounds'] = start_rounds
  db['elim'] = {album_title: {}}

def check_acronyms(user_input):
  if user_input.startswith("#"):
    acronym = user_input[1:]
    return db[acronym]
  else:
    return user_input

def check_saves_offs(album_title):
  tracklist = db[album_title]
  tracklist_length = len(tracklist.keys())
  saves = 0
  offs = 0
  if tracklist_length >= 14:
    saves = 5
    offs = saves - 1
  elif tracklist_length < 14 and tracklist_length >= 10:
    saves = 4
    offs = saves - 1
  elif tracklist_length < 10 and tracklist_length >= 6:
    saves = 3
    offs = saves - 1
  elif tracklist_length < 6 and tracklist_length > 3:
    saves = 0
    offs = 3
  elif tracklist_length == 3:
    saves = 0
    offs = 2
  elif tracklist_length == 2:
    saves = 0
    offs = 1

  check = [saves, offs]
  print(check)
  return check

@bot.command(name="scores")
async def print_scores(ctx, arg):
  album_title = check_acronyms(arg.lower())
  response, eliminated = scores(album_title)[0], scores(album_title)[1]
  embed = discord.Embed(title='Round {}'.format(db['album_rounds'][album_title]), color = 0x6eebff)
  embed.add_field(name='{}'.format(album_title), value=response+'\n'+eliminated)
  await ctx.send(embed=embed)

def scores(arg):
  sorted_db = dict(sorted(db[arg.lower()].items(), key=operator.itemgetter(1), reverse=True))
  response = ""
  eliminated = "Eliminated: \n"

  for key, value in sorted_db.items():
    response += "{}: {} \n".format(key, value)
  
  for key, value in db['elim'][arg.lower()].items():
    eliminated += "{}: {} \n".format(key, value)

  return [response, eliminated]

@bot.command(name="vote")
async def vote_tracks(ctx, arg):
  def verify(message):
      return message.channel == ctx.channel and message.author == ctx.author

  album_title = check_acronyms(arg.lower())

  if album_title in db.keys():
    check = check_saves_offs(album_title)
    if check[0] > 0:
      await ctx.send("Choose {} songs to save!".format(check[0]))
      saves = await bot.wait_for("message", check=verify)
      saves_newline = set(saves.content.split("\n"))
      if len(saves_newline) == check[0]:
        for save in saves_newline:
          if save.lower() in db[album_title].keys():
            scores = db[album_title]
            scores[save] += 1
            db[album_title] = scores
          else:
            await ctx.send("You picked a song that's misspelled, eliminated or doesn't exist on this album bestie. Please check.")
            return
      else:
        await ctx.send("You haven't picked the correct amount of songs to save, used the wrong format or maybe tried to vote for the same song twice. You thought bestie!")
        return 

    await ctx.send("Choose {} songs to off!".format(check[1]))
    offs = await bot.wait_for("message", check=verify)
    offs_newline = set(offs.content.split("\n"))
    if len(offs_newline) == check[1]:
      for off in offs_newline:
        if off.lower() in db[album_title].keys():
          scores = db[album_title]
          scores[off] -= 1
          db[album_title] = scores
        else:
            await ctx.send("You picked a song that's misspelled, eliminated or doesn't exist on this album bestie. Please check.")
    else:
      await ctx.send("You haven't picked the correct amount of songs to boot, used the wrong format or maybe tried to vote for the same song twice. You thought!")
  else:
    await ctx.send("This album does not have a survivor! Check for spelling...")


def round_calculator(album_title):
  sorted_tracklist = sorted(db[album_title].items(), key=operator.itemgetter(1), reverse=True)
  print(sorted_tracklist)

  if len(sorted_tracklist) < 6 and len(sorted_tracklist) >= 2:
    (win, win_score) = sorted_tracklist[0]
    (elim, elim_score) = sorted_tracklist[-1]
    safe = sorted_tracklist[1:-1]
    safe_print = ""
    for (x, y) in safe:
        safe_print += x + " - " + "[" + str(y) +"]"

    ranks = """WIN: \n {} - [{}] \n
    SAFE: \n {} \n
    ELIMINATED: \n {} - [{}]""".format(win, win_score, safe_print, elim, elim_score)

  elif len(sorted_tracklist) == 1:
    (win, win_score) = sorted_tracklist[0]
    ranks = (win, win_score)
    return ranks
  elif len(sorted_tracklist) == 0:
    ranks = list(db['elim'][album_title])
    return ranks[-1]
  else:
    (win, win_score) = sorted_tracklist[0]
    ((high1, high1_score), (high2, high2_score)) = sorted_tracklist[1], sorted_tracklist[2]
    ((low1, low1_score), (low2, low_2score)) = sorted_tracklist[-2], sorted_tracklist[-3]
    (elim, elim_score) = sorted_tracklist[-1]
    safe = sorted_tracklist[3:-3]

    safe_print = ""

    for (x, y) in safe:
        safe_print += x + " - " + "[" + str(y) +"]\n"

    ranks = """WIN: \n {} - [{}] \n
    HIGH: \n {} - [{}] \n {} - [{}] \n
    SAFE: \n {}
    LOW: \n {} - [{}] \n {} - [{}] \n
    ELIMINATED: \n {} - [{}]""".format(win, win_score, high1, high1_score, high2, high2_score, safe_print, low1, low1_score, low2, low_2score, elim, elim_score)

  if elim in db[album_title]:
    db['elim'][album_title][elim] = elim_score
    del db[album_title][elim]

  return ranks

@bot.command(name="round")
async def new_round(ctx, arg):
  album_title = check_acronyms(arg.lower())
  if album_title in db.keys():
    db['album_rounds'][album_title] += 1
    ranks = round_calculator(album_title)
    checks = check_saves_offs(album_title)
    embed = discord.Embed(title='Round {}'.format(db['album_rounds'][album_title]-1), color = 0x6eebff)
    embed.add_field(name='{}'.format(album_title), value=ranks)
    await ctx.send(embed=embed)
    if (checks[0]) == 0 and (checks[1]) == 0:
      await ctx.send("This survivor has now finished. The winner is " + ranks + "\n Thanks for playing!")
    else:
      await ctx.send("Starting a new round bestie...")
      response = "This is round " + str(db['album_rounds'][album_title]) + "\n Please save {} songs and off {} songs!".format(checks[0], checks[1])
      await ctx.send(response)
  else:
    await ctx.send("This album does not have a survivor or you made a typo. Please check bestie.")

@bot.command(name="survivor")
async def survivor(ctx, arg1, arg2):
    album_title = arg1.lower()
    mb_api = "https://musicbrainz.org/ws/2/release/{}?inc=recordings&fmt=json".format(arg2)
    tracklist = get_metadata(mb_api)
    if album_title not in db.keys():
      add_album(album_title, tracklist)

@bot.event
async def on_ready():
    await bot.change_presence(activity = discord.Activity(
                          type = discord.ActivityType.listening, 
                          name = ''))
    print(f'{bot.user} has connected to Discord!')

bot.run(my_secret)
