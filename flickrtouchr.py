#!/usr/bin/env python

#
# FlickrTouchr - a simple python script to grab all your photos from flickr, 
#                dump into a directory - organised into folders by set - 
#                along with any favourites you have saved.
#
#                You can then sync the photos to an iPod touch.
#
# Version:       1.2
#
# Original Author:	colm - AT - allcosts.net  - Colm MacCarthaigh - 2008-01-21
#
# Modified by:			Dan Benjamin - http://hivelogic.com										
#
# License:       		Apache 2.0 - http://www.apache.org/licenses/LICENSE-2.0.html
#

import getopt
import xml.dom.minidom
import webbrowser
import urlparse
import urllib2
import unicodedata
import cPickle
import md5
import sys
import os
import time

API_KEY       = "d2c232d91c218c0c2a9a79bf24193b9d"
SHARED_SECRET = "214e89bdb23881d7"
verbose       = False

#
# Utility functions for dealing with flickr authentication
#
def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc.encode("utf-8")

#
# Get the frob based on our API_KEY and shared secret
#
def getfrob():
    # Create our signing string
    string = SHARED_SECRET + "api_key" + API_KEY + "methodflickr.auth.getFrob"
    hash   = md5.new(string).digest().encode("hex")

    # Formulate the request
    url    = "http://api.flickr.com/services/rest/?method=flickr.auth.getFrob"
    url   += "&api_key=" + API_KEY + "&api_sig=" + hash

    try:
        # Make the request and extract the frob
        response = urllib2.urlopen(url)
    
        # Parse the XML
        dom = xml.dom.minidom.parse(response)

        # get the frob
        frob = getText(dom.getElementsByTagName("frob")[0].childNodes)

        # Free the DOM 
        dom.unlink()

        # Return the frob
        return frob

    except:
        raise "Could not retrieve frob"

#
# Login and get a token
#
def froblogin(frob, perms):
    string = SHARED_SECRET + "api_key" + API_KEY + "frob" + frob + "perms" + perms
    hash   = md5.new(string).digest().encode("hex")

    # Formulate the request
    url    = "http://api.flickr.com/services/auth/?"
    url   += "api_key=" + API_KEY + "&perms=" + perms
    url   += "&frob=" + frob + "&api_sig=" + hash

    # Tell the user what's happening
    print "In order to allow FlickrTouchr to read your photos and favourites"
    print "you need to allow the application. Please press return when you've"
    print "granted access at the following url (which should have opened"
    print "automatically)."
    print
    print url
    print 
    print "Waiting for you to press return"

    # We now have a login url, open it in a web-browser
    webbrowser.open_new(url)

    # Wait for input
    sys.stdin.readline()

    # Now, try and retrieve a token
    string = SHARED_SECRET + "api_key" + API_KEY + "frob" + frob + "methodflickr.auth.getToken"
    hash   = md5.new(string).digest().encode("hex")
    
    # Formulate the request
    url    = "http://api.flickr.com/services/rest/?method=flickr.auth.getToken"
    url   += "&api_key=" + API_KEY + "&frob=" + frob
    url   += "&api_sig=" + hash

    # See if we get a token
    try:
        # Make the request and extract the frob
        response = urllib2.urlopen(url)
    
        # Parse the XML
        dom = xml.dom.minidom.parse(response)

        # get the token and user-id
        token = getText(dom.getElementsByTagName("token")[0].childNodes)
        nsid  = dom.getElementsByTagName("user")[0].getAttribute("nsid")

        # Free the DOM
        dom.unlink()

        # Return the token and userid
        return (nsid, token)
    except:
        raise "Login failed"

# 
# Sign an arbitrary flickr request with a token
# 
def flickrsign(url, token):
    query  = urlparse.urlparse(url).query
    query += "&api_key=" + API_KEY + "&auth_token=" + token
    params = query.split('&') 

    # Create the string to hash
    string = SHARED_SECRET
    
    # Sort the arguments alphabettically
    params.sort()
    for param in params:
        string += param.replace('=', '')
    hash   = md5.new(string).digest().encode("hex")

    # Now, append the api_key, and the api_sig args
    url += "&api_key=" + API_KEY + "&auth_token=" + token + "&api_sig=" + hash
    
    # Return the signed url
    return url

#
# Grab a photo's raw exif xml from the server and write to disk
#
def getrawexif(id, token, path, usecached):
    try:
        # Local filename
        filename = path + "/" + id + "-exif.xml"

        if usecached and os.path.exists(filename):
          return filename

        # Contruct a request to find the exif
        url  = "http://api.flickr.com/services/rest/?method=flickr.photos.getExif"
        url += "&photo_id=" + id
    
        # Sign the request
        url = flickrsign(url, token)
    
        # Make the request
        response = urllib2.urlopen(url)
        responseString = response.read()
       
		# Write the XML to path + id . xml
        fh = open(filename, "w")
        fh.write(responseString)
        fh.close()

        return filename
    except:
        print "Failed to retrieve exif for id " + id
    

#
# Grab a photo's raw geo position xml from the server and write to disk
#
def getrawgeo(id, token, path, usecached):
    try:
        # Local filename
        filename = path + "/" + id + "-geo.xml"

        if usecached and os.path.exists(filename):
          return filename

        # Contruct a request to find the sizes
        url  = "http://api.flickr.com/services/rest/?method=flickr.photos.geo.getLocation"
        url += "&photo_id=" + id
    
        # Sign the request
        url = flickrsign(url, token)
    
        # Make the request
        response = urllib2.urlopen(url)
        responseString = response.read()
       
		# Write the XML to path + id . xml
        fh = open(filename, "w")
        fh.write(responseString)
        fh.close()

        return filename
    except:
        print "Failed to retrieve geo for id " + id
    

#
# Grab a photo's raw comment xml from the server and write to disk
#
def getrawcomments(id, token, path, usecached):
    try:
        # Local filename
        filename = path + "/" + id + "-comments.xml"

        if usecached and os.path.exists(filename):
          return filename

        # Contruct a request to find the sizes
        url  = "http://api.flickr.com/services/rest/?method=flickr.photos.comments.getList"
        url += "&photo_id=" + id
    
        # Sign the request
        url = flickrsign(url, token)
    
        # Make the request
        response = urllib2.urlopen(url)
        responseString = response.read()
       
		# Write the XML to path + id . xml
        fh = open(filename, "w")
        fh.write(responseString)
        fh.close()

        return filename
    except:
        print "Failed to retrieve comments for id " + id
    

#
# Grab a photo's raw metadata from the server and write to disk
#
def getrawmetadata(id, token, path, usecached, willgetcomments):
    try:
        # Local filename
        filename = path + "/" + id + "-metadata.xml"

        if usecached and os.path.exists(filename) and (not(willgetcomments) or os.path.exists(path + "/" + id + "-comments.xml")):
          return filename

        # Contruct a request to find the info
        url  = "http://api.flickr.com/services/rest/?method=flickr.photos.getInfo"
        url += "&photo_id=" + id
    
        # Sign the request
        url = flickrsign(url, token)
    
        # Make the request
        response = urllib2.urlopen(url)
        responseString = response.read()
        
		# Write the XML to path + id . xml
        fh = open(filename, "w")
        fh.write(responseString)
        fh.close()

        # Parse the XML
        dom = xml.dom.minidom.parseString(responseString)

        # Does the photo have comments? Do we want them?
        commentcount = int(getText(dom.getElementsByTagName("comments")[0].childNodes))
        if (commentcount > 0 and willgetcomments):
          getrawcomments(id, token, path, usecached)

        # Free the DOM memory
        dom.unlink()

        return filename
    except:
        print "Failed to retrieve metadata for id " + id
    

#
# Apply a Flickr XML "taken" timestamp to a file
# Arg 1 is the file to modify, Arg 2 is the path to a photos.getInfo Flickr XML response
#
def applytimestamp(filename, xmlpath):
    try:
        # Open described metadata
        mfh = open(xmlpath, "r")
        dom = xml.dom.minidom.parse(mfh)
        
		# Read the timestamp
        rawtimestamp = dom.getElementsByTagName("dates")[0].getAttribute("taken")

        # migrate time to system usable format
        # time format from flickr:     2010-11-08 00:17:19
        t = time.strptime(rawtimestamp, "%Y-%m-%d %H:%M:%S")

        # apply timestamp to file
        os.utime(filename,(time.mktime(t),time.mktime(t)))

        # Clean up
        dom.unlink()
        close(mfh)
        
        # Return success
        return True

    except:
        return False

#
# Grab the photo from the server
#
def getphoto(id, token, path):
#    try:
        # Contruct a request to find the sizes
        url  = "http://api.flickr.com/services/rest/?method=flickr.photos.getSizes"
        url += "&photo_id=" + id
    
        # Sign the request
        url = flickrsign(url, token)
    
        # Make the request
        response = urllib2.urlopen(url)
        
        # Parse the XML
        dom = xml.dom.minidom.parse(response)

        # Get the list of sizes
        sizes =  dom.getElementsByTagName("size")

        # Get the video or original url - video urls require a little effort
        isvideo = False
        downloadurl = ""
        for size in sizes:
          label = size.getAttribute("label")
          if label in "Site MP4":
            isvideo = True
            downloadurl = size.getAttribute("source")
          elif label in "Original" and not(isvideo):
            downloadurl = size.getAttribute("source")

        # Sanity check
        if len(downloadurl) == 0:
          print "Failed to get download source for id " + id
          return

        # Free the DOM memory
        dom.unlink()

        # Grab the file (we're not retrieving it yet, just getting details)
        response = urllib2.urlopen(downloadurl)
        # Get the 'real' filename (we may have been redirected)
        downloadurl = response.geturl()
        # Get the remote filesize before acting on anything
        remotesize = response.info().get('Content-Length')

        # Make our local filename, splitting to the first word (there may have been variables tacked to the end, i.e. mypic.jpg?hamburger=1)
        filename = path + "/" + os.path.basename(downloadurl.split("?", 1)[0])

        # Skip a file that exists and is the same size
        localsize = 0
        if os.access(filename, os.R_OK):
          localsize = os.stat(filename).st_size
          if int(remotesize) == int(localsize):
            print downloadurl + " is in sync with " + filename + " (" + str(localsize) + " bytes)"
            return filename

        # Determined we don't have it sync'd, go retrieve it
        print downloadurl + " (" + str(remotesize) + " bytes) -> " + filename + " (" + str(localsize) + " bytes)"
        data = response.read()
    
        # Save the file!
        fh = open(filename, "w")
        fh.write(data)
        fh.close()
		
        return filename
#    except:
#        print "Failed to retrieve photo for id " + id
    


#
# Grab a set's raw info xml from the server and write to disk
#
def getrawsetinfo(id, token, path, usecached):
    try:
        # Local filename
        filename = path + "/" + id + "-setinfo.xml"

        if usecached and os.path.exists(filename):
          return filename

        # Contruct a request to find the sizes
        url  = "http://api.flickr.com/services/rest/?method=flickr.photosets.getInfo"
        url += "&photo_id=" + id
    
        # Sign the request
        url = flickrsign(url, token)
    
        # Make the request
        response = urllib2.urlopen(url)
        responseString = response.read()
       
		# Write the XML to path + id . xml
        fh = open(filename, "w")
        fh.write(responseString)
        fh.close()

        return filename
    except:
        print "Failed to retrieve set info for id " + id
    

#
# Grab a set's raw comment xml from the server and write to disk
#
def getrawsetcomments(id, token, path, usecached):
    try:
        # Local filename
        filename = path + "/" + id + "-setcomments.xml"

        if usecached and os.path.exists(filename):
          return filename

        # Contruct a request to find the sizes
        url  = "http://api.flickr.com/services/rest/?method=flickr.photosets.comments.getList"
        url += "&photo_id=" + id
    
        # Sign the request
        url = flickrsign(url, token)
    
        # Make the request
        response = urllib2.urlopen(url)
        responseString = response.read()
       
		# Write the XML to path + id . xml
        fh = open(filename, "w")
        fh.write(responseString)
        fh.close()

        return filename
    except:
        print "Failed to retrieve set comments for id " + id
    

######## Usage #####################
def usage():
    print "usage: flickrtouchr.py"
    print ""
    print "-h, --help ............... This help section"
    print "-v, --verbose ............ Verbose debug output"
    print ""
    print "-d, --directory .......... (REQUIRED) Directory parent to place Flickr sets in"
    print "-t, --apply-timestamp .... Apply photo's taken timestamp local file timestamp (requires --include-metadata (-m))"
    print "-m, --include-metadata ... Retrieve Flickr XML metadata"
    print "-c, --include-comments ... Retrieve Flickr XML photo comments (requires --include-metadata (-m))"
    print "-g, --include-geo ........ Retrieve Flickr XML geo position data"
    print "-x, --include-exif ....... Retrieve Flickr XML exif data"
    print "-z, --use-cached-meta ......... Zzzz, use cached metadata (if it exists). Saves on web service calls."
    print ""
    print "Remember: Each added Flickr XML retrieval is a web service call per photo... The data costs a little time."


######## Main Application ##########
def main(argv):
    # The first, and only argument needs to be a directory
    try:
        opts, args = getopt.getopt(argv, "hvd:tmcgxz", ["help", "verbose", "directory=", "apply-timestamp", "include-metadata", "include-comments", "include-geo", "include-exif", "use-cached-meta"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    print opts

    # Before anything, validate command line...
    willapplytimestamp = False
    willgetmetadata = False
    willgetcomments = False
    willgetgeo = False
    willgetexif = False
    for opt, val in opts:
      if opt in ("-v", "--verbose"):
        verbose = True
      elif opt in ("-d", "--directory"):
        if os.path.exists(val):
          localpath = val
          os.chdir(localpath)
      elif opt in ("-t", "--apply-timestamp"):
        willapplytimestamp = True
      elif opt in ("-m", "--include-metadata"):
        willgetmetadata = True
      elif opt in ("-c", "--include-comments"):
        willgetcomments = True
      elif opt in ("-g", "--include-geo"):
        willgetgeo = True
      elif opt in ("-x", "--include-exif"):
        willgetexif = True
      elif opt in ("-z", "--use-cached-meta"):
        usecachedmeta = True
      else:
        usage()
        sys.exit()

    # Added sanity check against command line
    commandlineerror = False
    if (willapplytimestamp and not(willgetmetadata)):
      commandlineerror = True
    if (willgetcomments and not(willgetmetadata)):
      commandlineerror = True

    if commandlineerror:
      usage()
      sys.exit(2)
   

    if verbose:
      print "Working in: " + os.getcwd()

    # First things first, see if we have a cached user and auth-token
    try:
        if verbose:
          print "Checking Flickr auth-token..."
        cache = open("touchr.frob.cache", "r")
        config = cPickle.load(cache)
        cache.close()

    # We don't - get a new one
    except:
        if verbose:
          print "Failed to find or load auth-token, initiating new..."
        (user, token) = froblogin(getfrob(), "read")
        config = { "version":1 , "user":user, "token":token }  

        # Save it for future use
        cache = open("touchr.frob.cache", "w")
        cPickle.dump(config, cache)
        cache.close()

    # Get the user info
    url  = "http://api.flickr.com/services/rest/?method=flickr.people.getInfo"
    url += "&user_id=" + config["user"]
    url  = flickrsign(url, config["token"])

    # get the result
    response = urllib2.urlopen(url)
    
    # Parse the XML
    dom = xml.dom.minidom.parse(response)

    # Get our real name
    realname = getText(dom.getElementsByTagName("realname")[0].childNodes)
    if verbose:
      print "Hello " + realname
	
    # Get our photo count
    totalpiccount = int(getText(dom.getElementsByTagName("count")[0].childNodes))
    if verbose:
      print "You have " + str(totalpiccount) + " photos on Flickr."

    # Free the DOM memory
    dom.unlink()


    # Now, construct a query for the list of photo sets
    url  = "http://api.flickr.com/services/rest/?method=flickr.photosets.getList"
    url += "&user_id=" + config["user"]
    url  = flickrsign(url, config["token"])

    # get the result
    response = urllib2.urlopen(url)
    
    # Parse the XML
    dom = xml.dom.minidom.parse(response)

    # Get the list of Sets
    sets =  dom.getElementsByTagName("photoset")

    # For each set - create a url
    urls = []
    for set in sets:
        pid = set.getAttribute("id")
        dir = getText(set.getElementsByTagName("title")[0].childNodes)
        dir = unicodedata.normalize('NFKD', dir.decode("utf-8", "ignore")).encode('ASCII', 'ignore') # Normalize to ASCII

        # Build the list of photos
        url   = "http://api.flickr.com/services/rest/?method=flickr.photosets.getPhotos"
        url  += "&photoset_id=" + pid

        # Append to our list of urls
        urls.append( (url , dir) )
    
    # Free the DOM memory
    dom.unlink()

    # Add the photos which are not in any set
    url   = "http://api.flickr.com/services/rest/?method=flickr.photos.getNotInSet"
    urls.append( (url, "No Set") )

    # Add the user's Favourites
    url   = "http://api.flickr.com/services/rest/?method=flickr.favorites.getList"
    urls.append( (url, "Favourites") )

    # Time to get the photos
    totalpiccounter = 0
    urlnum = 0
    for (url , dir) in urls:
        urlnum = urlnum + 1

        # Create the directory
        try:
            os.makedirs(dir)
        except:
            pass

        # Get 500 results per page
        url += "&per_page=500"
        pages = page = 1

        while page <= pages: 
            request = url + "&page=" + str(page)

            # Sign the url
            request = flickrsign(request, config["token"])

            # Make the request
            response = urllib2.urlopen(request)

            # Parse the XML
            dom = xml.dom.minidom.parse(response)

            # Get the total pages
            pages = int(dom.getElementsByTagName("photo")[0].parentNode.getAttribute("pages"))
			
			#reset the pic counter and get the page's pic count
            picnum = 0
            piccount = len(dom.getElementsByTagName("photo"))

            # Grab the photos
            for photo in dom.getElementsByTagName("photo"):
                totalpiccounter = totalpiccounter + 1
                picnum = picnum + 1

                # Grab the id
                photoid = photo.getAttribute("id")
				
                # Grab the name (title)
                phototitle = photo.getAttribute("title")
				
                # Let the user know what we're up to
                print str(totalpiccounter) + "/" + str(totalpiccount) + ", set " + str(urlnum) + "/" + str(len(urls)) + ", page " + str(page) + "/" + str(pages) + ", pic " + str(picnum) + "/" + str(piccount) + " - Photo ID: " + str(photoid) + "..."
				
				# Retrieve it
                photofilename = ""
                photofilename = getphoto(photoid, config["token"], dir)

                # (maybe) do special stuff...
                metadatafilename = ""
                if willgetmetadata:
                  # Retrieve metadata
                  metadatafilename = getrawmetadata(photoid, config["token"], dir, usecachedmeta, willgetcomments)
                if willapplytimestamp:
                  if os.path.exists(photofilename) and os.path.exists(metadatafilename):
                    # Apply the timestamp
                    if verbose:
                      print "Applying timestamp from " + metadatafilename + " to " + photofilename
                    applytimestamp(photofilename, metadatafilename)
                if willgetgeo:
                  geofilename = getrawgeo(photoid, config["token"], dir, usecachedmeta)
                  if len(geofilename):
                    gotgeo = True
                if willgetexif:
                  exiffilename = getrawexif(photoid, config["token"], dir, usecachedmeta)
                  if len(exiffilename):
                    gotexif = True

				
            # Move on the next page
            page = page + 1
			
			

######## Command Options Grabber ###########
if __name__ == '__main__':
    main(sys.argv[1:])
