// 2>/dev/null; gcc -g -o glxgears glxgears.c -lGL -lGLU -lX11 -lm && exec ./glxgears "$@" ; exit 1

#include <X11/Xlib.h>
#include <GL/gl.h>
#include <GL/glx.h>
#include <GL/glu.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <unistd.h>
#include <time.h>
#include <string.h>
#include <getopt.h>
#include <X11/keysym.h>

#define GEAR_VERTEX(v, x, y, z) do { \
GLfloat v[3]; \
v[0] = x; v[1] = y; v[2] = z; \
glNormal3fv(v); \
glVertex3f(x, y, z); \
} while(0)

static GLfloat view_rotx = 20.0, view_roty = 30.0, view_rotz = 0.0;
static GLint gear1, gear2, gear3;
static GLfloat angle = 0.0;
static GLfloat zoom = -20.0;
static int mouse_x = 0, mouse_y = 0;
static int mouse_left_down = 0;

static void
gear(GLfloat inner_radius, GLfloat outer_radius, GLfloat width,
	GLint teeth, GLfloat tooth_depth)
{
	GLint i;
	GLfloat r0, r1, r2;
	GLfloat angle, da;
	GLfloat u, v, len;

	r0 = inner_radius;
	r1 = outer_radius - tooth_depth / 2.0;
	r2 = outer_radius + tooth_depth / 2.0;

	da = 2.0 * M_PI / teeth / 4.0;

	glShadeModel(GL_FLAT);

	glNormal3f(0.0, 0.0, 1.0);

	/* draw front face */
	glBegin(GL_QUAD_STRIP);
	for (i = 0; i <= teeth; i++) {
		angle = i * 2.0 * M_PI / teeth;
		glVertex3f(r0 * cos(angle), r0 * sin(angle), width * 0.5);
		glVertex3f(r1 * cos(angle), r1 * sin(angle), width * 0.5);
		if (i < teeth) {
			glVertex3f(r0 * cos(angle), r0 * sin(angle), width * 0.5);
			glVertex3f(r1 * cos(angle + 3 * da), r1 * sin(angle + 3 * da), width * 0.5);
		}
	}
	glEnd();

	/* draw front sides of teeth */
	glBegin(GL_QUADS);
	da = 2.0 * M_PI / teeth / 4.0;
	for (i = 0; i < teeth; i++) {
		angle = i * 2.0 * M_PI / teeth;

		glNormal3f(0.0, 0.0, 1.0);
		glVertex3f(r1 * cos(angle), r1 * sin(angle), width * 0.5);
		glVertex3f(r2 * cos(angle + da), r2 * sin(angle + da), width * 0.5);
		glVertex3f(r2 * cos(angle + 2 * da), r2 * sin(angle + 2 * da), width * 0.5);
		glVertex3f(r1 * cos(angle + 3 * da), r1 * sin(angle + 3 * da), width * 0.5);
	}
	glEnd();

	glNormal3f(0.0, 0.0, -1.0);

	/* draw back face */
	glBegin(GL_QUAD_STRIP);
	for (i = 0; i <= teeth; i++) {
		angle = i * 2.0 * M_PI / teeth;
		glVertex3f(r1 * cos(angle), r1 * sin(angle), -width * 0.5);
		glVertex3f(r0 * cos(angle), r0 * sin(angle), -width * 0.5);
		if (i < teeth) {
			glVertex3f(r1 * cos(angle + 3 * da), r1 * sin(angle + 3 * da), -width * 0.5);
			glVertex3f(r0 * cos(angle), r0 * sin(angle), -width * 0.5);
		}
	}
	glEnd();

	/* draw back sides of teeth */
	glBegin(GL_QUADS);
	da = 2.0 * M_PI / teeth / 4.0;
	for (i = 0; i < teeth; i++) {
		angle = i * 2.0 * M_PI / teeth;

		glNormal3f(0.0, 0.0, -1.0);
		glVertex3f(r1 * cos(angle + 3 * da), r1 * sin(angle + 3 * da), -width * 0.5);
		glVertex3f(r2 * cos(angle + 2 * da), r2 * sin(angle + 2 * da), -width * 0.5);
		glVertex3f(r2 * cos(angle + da), r2 * sin(angle + da), -width * 0.5);
		glVertex3f(r1 * cos(angle), r1 * sin(angle), -width * 0.5);
	}
	glEnd();

	/* draw outward faces of teeth */
	glBegin(GL_QUAD_STRIP);
	for (i = 0; i < teeth; i++) {
		angle = i * 2.0 * M_PI / teeth;

		u = r2 * cos(angle + da) - r1 * cos(angle);
		v = r2 * sin(angle + da) - r1 * sin(angle);
		len = sqrt(u * u + v * v);
		u /= len;
		v /= len;

		glNormal3f(v, -u, 0.0);
		glVertex3f(r1 * cos(angle), r1 * sin(angle), width * 0.5);
		glVertex3f(r1 * cos(angle), r1 * sin(angle), -width * 0.5);
		glVertex3f(r2 * cos(angle + da), r2 * sin(angle + da), width * 0.5);
		glVertex3f(r2 * cos(angle + da), r2 * sin(angle + da), -width * 0.5);

		u = r2 * cos(angle + 2 * da) - r2 * cos(angle + da);
		v = r2 * sin(angle + 2 * da) - r2 * sin(angle + da);
		len = sqrt(u * u + v * v);
		u /= len;
		v /= len;

		glNormal3f(v, -u, 0.0);
		glVertex3f(r2 * cos(angle + 2 * da), r2 * sin(angle + 2 * da), width * 0.5);
		glVertex3f(r2 * cos(angle + 2 * da), r2 * sin(angle + 2 * da), -width * 0.5);

		u = r1 * cos(angle + 3 * da) - r2 * cos(angle + 2 * da);
		v = r1 * sin(angle + 3 * da) - r2 * sin(angle + 2 * da);
		len = sqrt(u * u + v * v);
		u /= len;
		v /= len;

		glNormal3f(v, -u, 0.0);
		glVertex3f(r1 * cos(angle + 3 * da), r1 * sin(angle + 3 * da), width * 0.5);
		glVertex3f(r1 * cos(angle + 3 * da), r1 * sin(angle + 3 * da), -width * 0.5);
	}
	glVertex3f(r1 * cos(0), r1 * sin(0), width * 0.5);
	glVertex3f(r1 * cos(0), r1 * sin(0), -width * 0.5);
	glEnd();

	/* draw inside radius cylinder */
	glBegin(GL_QUAD_STRIP);
	for (i = 0; i <= teeth; i++) {
		angle = i * 2.0 * M_PI / teeth;
		glNormal3f(-cos(angle), -sin(angle), 0.0);
		glVertex3f(r0 * cos(angle), r0 * sin(angle), -width * 0.5);
		glVertex3f(r0 * cos(angle), r0 * sin(angle), width * 0.5);
	}
	glEnd();
}

static void
draw(void)
{
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

	glPushMatrix();
	glRotatef(view_rotx, 1.0, 0.0, 0.0);
	glRotatef(view_roty, 0.0, 1.0, 0.0);
	glRotatef(view_rotz, 0.0, 0.0, 1.0);

	glPushMatrix();
	glTranslatef(-3.0, -2.0, 0.0);
	glRotatef(angle, 0.0, 0.0, 1.0);
	glCallList(gear1);
	glPopMatrix();

	glPushMatrix();
	glTranslatef(3.1, -2.0, 0.0);
	glRotatef(-2.0 * angle - 9.0, 0.0, 0.0, 1.0);
	glCallList(gear2);
	glPopMatrix();

	glPushMatrix();
	glTranslatef(-3.1, 4.2, 0.0);
	glRotatef(-2.0 * angle - 25.0, 0.0, 0.0, 1.0);
	glCallList(gear3);
	glPopMatrix();

	glPopMatrix();
}

static void
init(void)
{
	static GLfloat pos[4] = {5.0, 5.0, 10.0, 0.0};
	static GLfloat red[4] = {0.8, 0.1, 0.0, 1.0};
	static GLfloat green[4] = {0.0, 0.8, 0.2, 1.0};
	static GLfloat blue[4] = {0.2, 0.2, 1.0, 1.0};

	glLightfv(GL_LIGHT0, GL_POSITION, pos);
	glEnable(GL_CULL_FACE);
	glEnable(GL_LIGHTING);
	glEnable(GL_LIGHT0);
	glEnable(GL_DEPTH_TEST);

	/* make the gears */
	gear1 = glGenLists(1);
	glNewList(gear1, GL_COMPILE);
	glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, red);
	gear(1.0, 4.0, 1.0, 20, 0.7);
	glEndList();

	gear2 = glGenLists(1);
	glNewList(gear2, GL_COMPILE);
	glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, green);
	gear(0.5, 2.0, 2.0, 10, 0.7);
	glEndList();

	gear3 = glGenLists(1);
	glNewList(gear3, GL_COMPILE);
	glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, blue);
	gear(1.3, 2.0, 0.5, 10, 0.7);
	glEndList();

	glEnable(GL_NORMALIZE);
}

static void
handle_mouse_button(XButtonEvent *event)
{
	if (event->button == Button1) {
		if (event->type == ButtonPress) {
			mouse_left_down = 1;
			mouse_x = event->x;
			mouse_y = event->y;
		} else if (event->type == ButtonRelease) {
			mouse_left_down = 0;
		}
	} else if (event->type == ButtonPress) {
		if (event->button == Button4) {
			zoom += 0.5;  // Zoom in
		} else if (event->button == Button5) {
			zoom -= 0.5;  // Zoom out
		}
	}
}

static void
handle_mouse_motion(XMotionEvent *event)
{
	if (mouse_left_down) {
		int dx = event->x - mouse_x;
		int dy = event->y - mouse_y;
		view_roty += dx * 0.5;
		view_rotx += dy * 0.5;
		mouse_x = event->x;
		mouse_y = event->y;
	}
}

static void
usage(char *argv0)
{
	fprintf(stderr, "Usage: %s [options]\n"
		"Options:\n"
		"  -d <displayname>  set the display to run on\n"
		"  -s                run in sRGB mode\n"
		"  -S                run in stereo mode\n"
		"  -m N              run in multisample mode with at least N samples\n"
		"  -I N              set swap interval to N frames (default 1)\n"
		"  -f                run in fullscreen mode\n"
		"  -g WxH+X+Y        window geometry\n"
		"  -i                display OpenGL renderer info\n"
		"  -h                display this help and exit\n", argv0);
}

int
main(int argc, char *argv[])
{
	Display *dpy;
	Window win;
	GLXContext ctx;
	XVisualInfo *vi;
	Colormap cmap;
	XSetWindowAttributes swa;
	GLXFBConfig *fbc;
	Atom wmDeleteMessage;
	int num_fbc;
	XWindowAttributes xwa;
	struct timespec start, end;
	double elapsed;

	// New variables for command line options
	char *displayName = NULL;
	int srgb = 0;
	int stereo = 0;
	int samples = 0;
	int swapInterval = 1;
	int fullscreen = 0;
	int showInfo = 0;
	char *geometry = NULL;

	// Parse command line options
	int opt;
	while ((opt = getopt(argc, argv, "d:sSm:I:fg:ih")) != -1) {
		switch (opt) {
			case 'd': displayName = optarg; break;
			case 's': srgb = 1; break;
			case 'S': stereo = 1; break;
			case 'm': samples = atoi(optarg); break;
			case 'I': swapInterval = atoi(optarg); break;
			case 'f': fullscreen = 1; break;
			case 'g': geometry = optarg; break;
			case 'i': showInfo = 1; break;
			case 'h':
			default:
				usage(argv[0]);
				exit(opt == 'h' ? 0 : 1);
		}
	}

	dpy = XOpenDisplay(displayName);
	if (dpy == NULL) {
		printf("Failed to open display\n");
		exit(1);
	}

	// Set up GLX attributes based on command line options
	int glx_attribs[16];  // Increased size to prevent overflow
	int index = 0;

	glx_attribs[index++] = GLX_RENDER_TYPE;
	glx_attribs[index++] = GLX_RGBA_BIT;
 	glx_attribs[index++] = GLX_DOUBLEBUFFER;
	glx_attribs[index++] = True;
 	glx_attribs[index++] = GLX_DEPTH_SIZE;
 	glx_attribs[index++] = 24;

	if (srgb) {
	    glx_attribs[index++] = GLX_FRAMEBUFFER_SRGB_CAPABLE_ARB;
	    glx_attribs[index++] = True;
	}

	if (stereo) {
	    glx_attribs[index++] = GLX_STEREO;
	    glx_attribs[index++] = True;
	}

	if (samples) {
	    glx_attribs[index++] = GLX_SAMPLE_BUFFERS;
	    glx_attribs[index++] = 1;
	    glx_attribs[index++] = GLX_SAMPLES;
	    glx_attribs[index++] = samples;
	}

	// Terminate the attribute list with None
	glx_attribs[index] = None;

	fbc = glXChooseFBConfig(dpy, DefaultScreen(dpy), glx_attribs, &num_fbc);
	if (fbc == NULL) {
		printf("Failed to find a suitable framebuffer config\n");
		exit(1);
	}

	vi = glXGetVisualFromFBConfig(dpy, fbc[0]);

	cmap = XCreateColormap(dpy, RootWindow(dpy, vi->screen), vi->visual, AllocNone);

	swa.colormap = cmap;
	swa.border_pixel = 0;
	swa.event_mask = StructureNotifyMask | ExposureMask | KeyPressMask | ButtonPressMask | ButtonReleaseMask | PointerMotionMask;

	int width = 600, height = 600, x = 0, y = 0;
	if (geometry) {
		sscanf(geometry, "%dx%d+%d+%d", &width, &height, &x, &y);
	}

	if (fullscreen) {
		width = DisplayWidth(dpy, DefaultScreen(dpy));
		height = DisplayHeight(dpy, DefaultScreen(dpy));
		x = y = 0;
	}

	win = XCreateWindow(dpy, RootWindow(dpy, vi->screen), x, y, width, height, 0, vi->depth, InputOutput, vi->visual, CWBorderPixel | CWColormap | CWEventMask, &swa);

	wmDeleteMessage = XInternAtom(dpy, "WM_DELETE_WINDOW", False);
	XSetWMProtocols(dpy, win, &wmDeleteMessage, 1);

	XMapWindow(dpy, win);
	XStoreName(dpy, win, "GLX Gears v1.0.4");

	ctx = glXCreateNewContext(dpy, fbc[0], GLX_RGBA_TYPE, 0, True);
	glXMakeCurrent(dpy, win, ctx);

	// Set swap interval
	typedef void (*PFNGLXSWAPINTERVALEXTPROC)(Display*, GLXDrawable, int);
	PFNGLXSWAPINTERVALEXTPROC glXSwapIntervalEXT = (PFNGLXSWAPINTERVALEXTPROC)glXGetProcAddress((const GLubyte*)"glXSwapIntervalEXT");
	if (glXSwapIntervalEXT) {
		glXSwapIntervalEXT(dpy, win, swapInterval);
	}

	init();

	if (showInfo) {
		printf("GL_RENDERER   = %s\n", (char *) glGetString(GL_RENDERER));
		printf("GL_VERSION    = %s\n", (char *) glGetString(GL_VERSION));
		printf("GL_VENDOR     = %s\n", (char *) glGetString(GL_VENDOR));
	}

	XGetWindowAttributes(dpy, win, &xwa);
	glViewport(0, 0, xwa.width, xwa.height);
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	gluPerspective(45.0, (float)xwa.width / (float)xwa.height, 0.1, 100.0);
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	glTranslatef(0.0, 0.0, zoom);

	while (1) {
		clock_gettime(CLOCK_MONOTONIC, &start);

		while (XPending(dpy)) {
			XEvent xev;
			XNextEvent(dpy, &xev);
			if (xev.type == ClientMessage) {
				if (xev.xclient.data.l[0] == wmDeleteMessage) {
					goto cleanup;
				}
			}
			else if (xev.type == Expose || xev.type == ConfigureNotify) {
				XGetWindowAttributes(dpy, win, &xwa);
				glViewport(0, 0, xwa.width, xwa.height);
				glMatrixMode(GL_PROJECTION);
				glLoadIdentity();
				gluPerspective(45.0, (float)xwa.width / (float)xwa.height, 0.1, 100.0);
				glMatrixMode(GL_MODELVIEW);
			}
			else if (xev.type == KeyPress) {
				KeySym key;
				char buffer[1];
				XLookupString(&xev.xkey, buffer, 1, &key, NULL);
				if (key == XK_q || key == XK_Escape) {
					goto cleanup;
				}
			}
			else if (xev.type == ButtonPress || xev.type == ButtonRelease) {
				handle_mouse_button(&xev.xbutton);
			}
			else if (xev.type == MotionNotify) {
				handle_mouse_motion(&xev.xmotion);
			}
		}

		angle += 0.5;
		glLoadIdentity();
		glTranslatef(0.0, 0.0, zoom);
		draw();
		glXSwapBuffers(dpy, win);

		clock_gettime(CLOCK_MONOTONIC, &end);
		elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
		if (elapsed < 1.0/60.0) {
			usleep((1.0/60.0 - elapsed) * 1e6);
		}
	}

cleanup:
	glXMakeCurrent(dpy, None, NULL);
	glXDestroyContext(dpy, ctx);
	XDestroyWindow(dpy, win);
	XCloseDisplay(dpy);

	return 0;
}
