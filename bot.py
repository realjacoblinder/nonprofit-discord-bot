import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import asyncio
from datetime import datetime
import requests
import urllib.parse

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='?')


@bot.command(name='npsearch')
async def search(ctx, *args):
    query = " ".join(args[:])
    query = query.strip()
    print(query)
    search_r = asyncio.get_event_loop()
    future = search_r.run_in_executor(None, requests.get, 'https://projects.propublica.org/nonprofits/api/v2/search.json?q={}'.format(urllib.parse.quote(query)))
    results = await future
    results = results.json()
    if 1 < results['total_results']:
        answer = str(results['total_results']) + ' results. Printing first 15. Try again with further specificity if needed. Otherwise use one of the following EIN numbers with the npein command.\n'
        for org in results['organizations'][1:15]:
            answer = answer + org['name'] + ': ' + str(org['ein']) + '\n'
        await ctx.send(answer)
    elif results['total_results'] == 0:
        await ctx.send('No results. Search smarter, not harder.')
    else:
        await ctx.send('Exactly one result. Processing...')
        ein = results['organizations'][0]['ein']
        await ein_search(ctx, ein)

@bot.command(name='npein')
async def ein_search(ctx, ein: int):
    ein_r = asyncio.get_event_loop()
    future = ein_r.run_in_executor(None, requests.get, 'https://projects.propublica.org/nonprofits/api/v2/organizations/{}.json'.format(str(ein)))
    results = await future
    results = results.json()
    if "status" in results:
        await ctx.send('EIN not found')
        return
    data = {}
    for item in results['filings_with_data']:
        new_key = item['tax_prd']
        data[new_key] = {}
        if item['formtype'] == 0: data[new_key]['Form'] = '990'
        elif item['formtype'] == 1: data[new_key]['Form'] = '990_EZ'
        elif item['formtype'] == 2: data[new_key]['Form'] = '990-PF'
        else: data[new_key]['Form'] = 'Unknown'
        data[new_key]['Revenue'] = item['totrevenue']
        data[new_key]['Expenses'] = item['totfuncexpns']
        data[new_key]['Liabilities'] = item['totliabend']
        data[new_key]['PDF'] = item['pdf_url'] if item['pdf_url'] else "Unavailable"
    for item in results['filings_without_data']:
        new_key = item['tax_prd']
        data[new_key] = {}
        if item['formtype'] == 0: data[new_key]['Form'] = '990'
        elif item['formtype'] == 1: data[new_key]['Form'] = '990_EZ'
        elif item['formtype'] == 2: data[new_key]['Form'] = '990-PF'
        else: data[new_key]['Form'] = 'Unknown'
        data[new_key]['Revenue'] = 'Unavailable'
        data[new_key]['Expenses'] = 'Unavailable'
        data[new_key]['Liabilities'] = 'Unavailable'
        data[new_key]['PDF'] = item['pdf_url'] if item['pdf_url'] else "Unavailable"
    return_string = ''
    for tax_prd in sorted(data, reverse=True):
        return_string += 'Tax Period: ' + datetime.strptime(str(tax_prd),'%Y%m').strftime('%m-%Y') + '\n'
        return_string += 'Form Type: ' + data[tax_prd]['Form'] + '\n'
        return_string += 'Revenue: $' + str(data[tax_prd]['Revenue']) + '\n'
        return_string += 'Expenses: $' + str(data[tax_prd]['Expenses']) + '\n'
        return_string += 'Liabilities: $' + str(data[tax_prd]['Liabilities']) + '\n'
        return_string += 'PDF link: ' + data[tax_prd]['PDF']
    await ctx.send(return_string)
bot.run(TOKEN)
