from quart import Quart
import weakref

app = Quart(__name__)
app.pc_pool = weakref.WeakSet()  # Store WebRTC peer connections

if __name__ == '__main__':
    app.run(debug=True)
