
import sys, os
import urllib2

url = sys.argv[1]

response = urllib2.urlopen(url)
html = response.read()
html_lines = html.split('\n')

dl_paths = []

for html_line in html_lines:
    if html_line.find('_vbr.mp3') != -1:
        first_quote = html_line.find('"')
        second_quote = html_line.find('"', first_quote+1)
        dl_paths.append(html_line[first_quote+1:second_quote])

if url[-1] == '/':
    url = url[:-1]

show_base = url.split('/')[-1]
show_name = show_base.split('.')[0]

target_dir = '%s/Desktop/%s' % (os.getenv('HOME'), show_name)

print 'Downloading %d files to %s...' % (len(dl_paths), target_dir)
os.makedirs(target_dir)

for dl_i, dl_path in enumerate(dl_paths):
    sys.stdout.write('Downloading file %d of %d, %s...' % (dl_i+1, len(dl_paths), dl_path))
    sys.stdout.flush()
    f = urllib2.urlopen('%s/%s' % (url, dl_path))
    with open('%s/%s' % (target_dir, dl_path), 'wb') as local_file:
        local_file.write(f.read())
    print 'done.'
