import React from 'react'
import { render, screen } from '@testing-library/react'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

describe('Table', () => {
  it('renders table with data', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Alice</TableCell>
            <TableCell>alice@example.com</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByText('Name')).toBeDefined()
    expect(screen.getByText('Email')).toBeDefined()
    expect(screen.getByText('Alice')).toBeDefined()
    expect(screen.getByText('alice@example.com')).toBeDefined()
  })

  it('renders table footer', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Data</TableCell>
          </TableRow>
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell>Footer</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    )
    expect(screen.getByText('Footer')).toBeDefined()
  })

  it('renders table caption', () => {
    render(
      <Table>
        <TableCaption>User list</TableCaption>
        <TableBody>
          <TableRow>
            <TableCell>Data</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(screen.getByText('User list')).toBeDefined()
  })
})
