#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <zlib.h>

#define TRUE  1
#define FALSE 0

#define BLYTE_PATH "/usr/local/blyte"

#define DECOMP_ERROR "Decompression failed"

static void error(char* msg, int appendErrno)
{
    if (appendErrno)
    {
        fprintf(stderr, "Error: %s (%s)\n", msg, strerror(errno));
    }
    else
    {
        fprintf(stderr, "Error: %s\n", msg);
    }

    exit(1);
}

typedef struct
{
    char name[512];
    uint8_t* data;
    int dataSize;
} fileStruct;

uint8_t unscrambleChar(uint8_t ch)
{
    if (ch >= 77)
    {
        return ch - 77;
    }
    else
    {
        return ch + (256 - 77);
    }
}

void unscramble(uint8_t* block, int blockSize, fileStruct* fs)
{
    int i;
    int nameDone = 0;
    uint8_t* blockStart = block;

    for (i = 0; i < blockSize; i++, block++)
    {
        int ch = unscrambleChar(*block);

        *block = ch;

        if (!nameDone)
        {
            if (ch == '*')
            {
                memcpy(fs->name, blockStart, i);
                fs->name[i] = '\0';

                fs->data = block + 1;
                fs->dataSize = blockSize - i - 1;

                nameDone = 1;
            }
        }
    }
}

int main(int argc, char** argv)
{
    /* $HOME/.oskusoft-tmp */
    char tmpDir[1024];

    /* $HOME/.blyte */
    char bconfdir[1024];

    /* $HOME/.blyte/lock */
    char lockfile[1024];

    char tmpBuf[1024];

    char* home = getenv("HOME");
    int ret, pid;
    int lockFd;
    struct flock fl;

    if (!home || (strlen(home) == 0))
    {
        error("HOME not set", FALSE);
    }

    /* the string '.oskusoft-tmp' is divided into parts to avoid it
       showing up on a simple 'strings blyte'. */
    snprintf(tmpDir, sizeof(tmpDir), "%s/.%s%s%s-%s", home, "osk", "uso",
        "ft", "tmp");
    snprintf(bconfdir, sizeof(bconfdir), "%s/.%s", home, "blyte");
    snprintf(lockfile, sizeof(lockfile), "%s/%s", bconfdir, "lock");

    ret = mkdir(bconfdir, S_IRWXU);
    if ((ret == -1) && (errno != EEXIST))
    {
        error("Couldn't create $HOME/.blyte directory", TRUE);
    }

    lockFd = open(lockfile, O_RDWR | O_CREAT, S_IRWXU);
    if (lockFd == -1)
    {
        error("Couldn't create lock file", TRUE);
    }

    fl.l_type = F_WRLCK;
    fl.l_whence = SEEK_SET;
    fl.l_start = 0;
    fl.l_len = 0;

    ret = fcntl(lockFd, F_SETLK, &fl);
    if (ret == -1)
    {
        error("Couldn't lock lock file, another Blyte process is probably"
            " running", FALSE);
    }

    snprintf(tmpBuf, sizeof(tmpBuf), "/bin/rm -rf %s", tmpDir);
    system(tmpBuf);

    ret = mkdir(tmpDir, S_IRWXU);
    if (ret == -1)
    {
        error("Couldn't create temporary directory", TRUE);
    }

    {
        uint8_t buf[512000];
        uint8_t* curPtr;
        uint8_t* lastPtr;
        int firstBlock = 1;

        int arcFd = open(BLYTE_PATH "/data.dat", O_RDONLY);
        if (arcFd == -1)
        {
            error("Couldn't open data.dat", TRUE);
        }

        ret = read(arcFd, buf, sizeof(buf));
        if (ret <= 0)
        {
            error("Error reading data.dat", TRUE);
        }

        close(arcFd);

        lastPtr = buf + ret - 1;

        /* skip 3 junk bytes at start */
        curPtr = buf + 3;

        while (1)
        {
            uint8_t buf2[512000];
            z_stream zs;
            fileStruct fs;
            int blockSize;

            if (curPtr > lastPtr)
            {
                break;
            }

            /* size of next zlib block */
            blockSize = 0;

            /* first block has the zero omitted */
            if (!firstBlock)
            {
                blockSize += *curPtr++ << 16;
            }

            blockSize += *curPtr++ << 8;
            blockSize += *curPtr++;

            zs.next_in = curPtr;
            zs.avail_in = blockSize;

            zs.next_out = buf2;
            zs.avail_out = sizeof(buf2);

            zs.zalloc = Z_NULL;
            zs.zfree = Z_NULL;
            zs.opaque = Z_NULL;

            if (inflateInit(&zs) != Z_OK)
            {
                error(DECOMP_ERROR, FALSE);
            }

            if (inflate(&zs, Z_FINISH) != Z_STREAM_END)
            {
                error(DECOMP_ERROR, FALSE);
            }

            if (inflateEnd(&zs) != Z_OK)
            {
                error(DECOMP_ERROR, FALSE);
            }

            if (!firstBlock)
            {
                int tmpFd;

                unscramble(buf2, zs.total_out, &fs);

                snprintf(tmpBuf, sizeof(tmpBuf), "%s/%s", tmpDir, fs.name);

                tmpFd = open(tmpBuf, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
                if (tmpFd == -1)
                {
                    error("Couldn't create temp file", TRUE);
                }

                ret = write(tmpFd, fs.data, fs.dataSize);
                if (ret != fs.dataSize)
                {
                    error("Error writing temp file", TRUE);
                }

                close(tmpFd);
            }

            curPtr += blockSize;
            firstBlock = 0;
        }
    }

    pid = fork();
    if (pid == -1)
    {
        error("fork failed", TRUE);
    }

    if (pid == 0)
    {
        int i;
        char** args = malloc(sizeof(char*) * (4 + argc - 1 + 1));

        args[0] = "/usr/bin/env";
        args[1] = "python";
        args[2] = "-O";
        args[3] = "blyte.pyo";

        for (i = 1; i < argc; i++)
        {
            args[3 + i] = argv[i];
        }

        args[3 + i] = NULL;

        ret = close(lockFd);
        if (ret == -1)
        {
            error("closing lock file failed", TRUE);
        }

        ret = chdir(tmpDir);
        if (ret == -1)
        {
            error("chdir failed", TRUE);
        }

        execv("/usr/bin/env", args);

        error("execl failed", TRUE);
    }
    else
    {
        waitpid(pid, NULL, 0);

        snprintf(tmpBuf, sizeof(tmpBuf), "/bin/rm -rf %s", tmpDir);
        system(tmpBuf);
    }

    return 0;
}
