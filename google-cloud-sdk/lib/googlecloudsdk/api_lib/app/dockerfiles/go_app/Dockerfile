# Dockerfile extending the generic Go image with application files for a
# single application.
FROM gcr.io/google_appengine/golang

# To enable Go 1.5 vendoring, uncomment the following line.
# For Go 1.5 vendoring details, see the documentation for the go command:
# https://golang.org/cmd/go/#hdr-Vendor_Directories
# and the design document: https://golang.org/s/go15vendor
# ENV GO15VENDOREXPERIMENT 1

COPY . /go/src/app
RUN go-wrapper install -tags appenginevm
