from aiohttp import web

async def handle(request):
    return web.Response(text="Bot Alive")

app = web.Application()
app.router.add_get('/', handle)

def run():
    web.run_app(app, port=10000)
