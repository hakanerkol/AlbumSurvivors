from misc import *
from keep_alive import keep_alive
from replit import db
from discord.ext import commands
import os
import operator
import discord
import requests
import random

keep_alive()
my_secret = os.environ['TOKEN']
bot = commands.Bot(command_prefix='%')

def get_metadata(mb_api):
  response = requests.get(mb_api)
  json_data = response.json()
  tracklist = {}
  for dicts in json_data['media'][0]['tracks']:
    if 'title' and 'number' in dicts:
      tracklist[dicts['title'].lower()] = dicts['number']
  
  return tracklist

def add_album(album_title, tracklist):
  split_title = album_title.split()
  acronym = ""
  for word in split_title:
    acronym += word[0]

  db[acronym] = album_title
  album_scores = {}

  for title, number in tracklist.items():
      album_scores[title] = 0

  db[album_title] = {}
  db[album_title]['album_scores'] = album_scores
  db[album_title]['tracklist'] = tracklist
  start_rounds = {album_title: 1}
  db['album_rounds'] = start_rounds
  db['elim'] = {album_title: {}}
  current_round = 1
  db[album_title]['vote_check'] = {current_round: []}

def check_acronyms(user_input):
  if user_input.startswith("#"):
    acronym = user_input[1:]
    print(db[acronym])
    return db[acronym]
  else:
    return user_input

def convert_numbers(user_input):
  pass

def check_saves_offs(album_title):
  tracklist = db[album_title]['album_scores']
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
  return check

@bot.command(name="scores")
async def print_scores(ctx, arg):
  album_title = check_acronyms(arg.lower())
  response_list = scores(album_title)
  response, eliminated = response_list[0], response_list[1]
  embed = discord.Embed(title='Round {}'.format(db['album_rounds'][album_title]), color = 0x6eebff)
  embed.add_field(name='{}'.format(album_title), value=response+'\n'+eliminated)
  await ctx.send(embed=embed)

def scores(arg):
  sorted_db = dict(sorted(db[arg.lower()]['album_scores'].items(), key=operator.itemgetter(1), reverse=True))
  response = ""
  eliminated = "Eliminated: \n"

  for key, value in sorted_db.items():
    position = db[arg.lower()]['tracklist'][key]
    response += "{}. {}: {} \n".format(position, key, value)
  
  for key, value in db['elim'][arg.lower()].items():
    position = db[arg.lower()]['tracklist'][key]
    eliminated += "{}. {}: {} \n".format(position, key, value)

  return [response, eliminated]

def vote_check(album_title, username):
  current_round = str(db['album_rounds'][album_title])
  print(db[album_title]['vote_check'][current_round])
  if current_round in db[album_title]['vote_check']:
    if username in db[album_title]['vote_check'][current_round]:
      return True
    return False

@bot.command(name="vote")
async def vote_tracks(ctx, arg):
  def verify(message):
      return message.channel == ctx.channel and message.author == ctx.author 

  album_title = check_acronyms(arg.lower())

  if vote_check(album_title, ctx.message.author.name):
    await ctx.send("You already voted for this survivor bestie, {}! Stop this nonsense.".format(ctx.message.author.name))
    return

  if album_title in db.keys():
    check = check_saves_offs(album_title)
    if check[0] > 0:
      await ctx.send("Choose {} songs to save, {}!".format(check[0], ctx.message.author.name))
      saves = await bot.wait_for("message", check=verify)
      saves_newline = set(saves.content.split("\n"))
      print(db[album_title]['album_scores'])
      print(db[album_title]['tracklist'])
      if len(saves_newline) == check[0]:
        for save in saves_newline:
          save = save.lower().strip()
          if save in db[album_title]['album_scores'].keys():
            scores = db[album_title]['album_scores']
            scores[save] += 1
            db[album_title]['album_scores'] = scores
          elif save in db[album_title]['tracklist'].values():
            scores = db[album_title]['album_scores']
            check_save = [k for k, v in db[album_title]['tracklist'].items() if v == save][0]
            if check_save in scores:
              scores[check_save] += 1
              db[album_title]['album_scores'] = scores
            else:
              await ctx.send("Hmm, there seems to be an error with the track {}. Make sure it has not been eliminated and vote again!".format(check_save))
              return
          else:
            await ctx.send("Hmm, there seems to be an error with the track title {}. It could be misspelled, eliminated or doesn't exist on this album bestie. Please check and vote again.".format(save))
            return
      else:
        await ctx.send("You haven't picked the correct amount of songs to save, used the wrong format or maybe tried to vote for the same song twice. You thought bestie!")
        return 

    await ctx.send("Choose {} songs to off, {}!".format(check[1], ctx.message.author.name))
    offs = await bot.wait_for("message", check=verify)
    offs_newline = set(offs.content.split("\n"))
    if len(offs_newline) == check[1]:
      for off in offs_newline:
        off = off.lower().strip()
        if off in db[album_title]['album_scores'].keys():
          scores = db[album_title]['album_scores']
          scores[off] -= 1
          db[album_title]['album_scores'] = scores
        elif off in db[album_title]['tracklist'].values():
          scores = db[album_title]['album_scores']
          check_off = [k for k, v in db[album_title]['tracklist'].items() if v == off][0]
          if check_off in scores:
            scores[check_off] -= 1
            db[album_title]['album_scores'] = scores
          else:
            await ctx.send("Hmm, there seems to be an error with the track number {}. Make sure it has not been eliminated and vote again!".format(off))
            return
        else:
          await ctx.send("Hmm, there seems to be an error with the track title {}. It could be misspelled, eliminated or doesn't exist on this album bestie. Please check and vote again.".format(off))
          return
    else:
      await ctx.send("You haven't picked the correct amount of songs to boot, used the wrong format or maybe tried to vote for the same song twice. Please use %vote album_title and put each song title on its own line.")
      return
  else:
    await ctx.send("This album does not have a survivor! Check for spelling...")
    return

  up = "👍"
  down = "👎"
  valid_reactions = ['👍', '👎']

  msg = await ctx.send("Confirm your votes bestie, {}!".format(ctx.message.author.name))
  await msg.add_reaction("👍")
  await msg.add_reaction("👎")

  def check(reaction, user):
    return user == ctx.author and str(reaction.emoji) in valid_reactions

  reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)

  if str(reaction.emoji) == up:
    messages = ["....werq I guess.", "Well everyone does have a right to vote...", "Trash, as expected, but your vote has been counted!", "Hmmm... Well we can't all have taste!"]
    response = " Thanks bestie, {}!".format(ctx.message.author.name)
    await ctx.send(random.choice(messages)+response)

    current_round = str(db['album_rounds'][album_title])
    if current_round in db[album_title]['vote_check']:
      db[album_title]['vote_check'][current_round].append(ctx.message.author.name)
    

  elif str(reaction.emoji) == down:
    try:
        for save in saves_newline:
          save = save.lower().strip()
          if save in db[album_title]['album_scores'].keys():
            scores = db[album_title]['album_scores']
            scores[save] += 1
            db[album_title]['album_scores'] = scores
          elif save in db[album_title]['tracklist'].values():
            scores = db[album_title]['album_scores']
            check_save = [k for k, v in db[album_title]['tracklist'].items() if v == save][0]
            if check_save in scores:
              scores[check_save] -= 1
              db[album_title]['album_scores'] = scores
    except UnboundLocalError:
      pass
    try:
      for off in offs_newline:
        off = off.lower().strip()
        if off in db[album_title]['album_scores'].keys():
          scores = db[album_title]['album_scores']
          scores[off] += 1
          db[album_title]['album_scores'] = scores
        elif off in db[album_title]['tracklist'].values():
          scores = db[album_title]['album_scores']
          check_off = [k for k, v in db[album_title]['tracklist'].items() if v == off][0]
          if check_off in scores:
            scores[check_off] += 1
            db[album_title]['album_scores'] = scores
      await ctx.send("Your vote has not been counted. Please vote again bestie, {}!".format(ctx.message.author.name))
    except UnboundLocalError:
      pass


def round_calculator(album_title):
  sorted_tracklist = sorted(db[album_title]['album_scores'].items(), key=operator.itemgetter(1), reverse=True)

  positions = []
  for x, y in sorted_tracklist:
    title = x
    for key, value in db[album_title]['tracklist'].items():
      if title == key:
        positions.append((value, key, y))

  print(positions)

  if len(sorted_tracklist) <= 6 and len(sorted_tracklist) > 2:
    (win_position, win, win_score) = positions[0]
    (elim_position, elim, elim_score) = positions[-1]
    safe = positions[1:-1]
    safe_print = ""
    for (x, y, z) in safe:
        safe_print += str(x) + ". " + y + " - " + "[" + str(z) +"]\n"

    ranks = """WIN: \n {}. {} - [{}] \n
    SAFE: \n {}
    ELIMINATED: \n {}. {} - [{}]""".format(win_position, win, win_score, safe_print, elim_position, elim, elim_score)

  elif len(sorted_tracklist) == 2:
    (win_position, win, win_score) = positions[0]
    (elim_position, elim, elim_score) = positions[1]
    ranks = """WINNER: \n {} - [{}] \n 
    ELIMINATED: \n {} - [{}]""".format(win_position, win, win_score, elim_position, elim, elim_score)

  elif len(sorted_tracklist) == 1:
    (win, win_score) = sorted_tracklist[0]
    ranks = """WINNER: \n {} - [{}] \n 
    """.format(win, win_score)
    return ranks
    
  else:
    (win_position, win, win_score) = positions[0]
    ((high1_position, high1, high1_score), (high2_position, high2, high2_score)) = positions[1], positions[2]
    ((low1_position, low1, low1_score), (low2_position, low2, low_2score)) = positions[-2], positions[-3]
    (elim_position, elim, elim_score) = positions[-1]
    safe = positions[3:-3]

    safe_print = ""

    for (x, y, z) in safe:
        safe_print += str(x) + ". " + y + " - " + "[" + str(z) +"]\n"

    ranks = """WIN: \n {}. {} - [{}] \n
    HIGH: \n {}. {} - [{}] \n {}. {} - [{}] \n
    SAFE: \n {}
    LOW: \n {}. {} - [{}] \n {}. {} - [{}] \n
    ELIMINATED: \n {}. {} - [{}]""".format(win_position, win, win_score, high1_position, high1, high1_score, high2_position, high2, high2_score, safe_print, low1_position, low1, low1_score, low2_position, low2, low_2score, elim_position,elim, elim_score)

  if elim in db[album_title]['album_scores']:
    db['elim'][album_title][elim] = elim_score
    del db[album_title]['album_scores'][elim]

  return ranks

@bot.command(name="round")
async def new_round(ctx, arg):
  album_title = check_acronyms(arg.lower())
  if album_title in db.keys():
    db['album_rounds'][album_title] += 1
    current_round = db['album_rounds'][album_title]
    db[album_title]['vote_check'][current_round] = []
    ranks = round_calculator(album_title)
    checks = check_saves_offs(album_title)
    embed = discord.Embed(title='Round {}'.format(db['album_rounds'][album_title]-1), color = 0x6eebff)
    embed.add_field(name='{}'.format(album_title), value=ranks)
    await ctx.send(embed=embed)
    if (checks[0]) == 0 and (checks[1]) == 0:
      await ctx.send("This survivor has now finished. Thanks for playing!")
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

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"{bot.latency}")

bot.run(my_secret)